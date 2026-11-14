"""Bounded local CRI @UTF/AFS2 reader; source layout checked against UmaViewer."""
import struct

FORMATS=('B','b','H','h','I','i','Q','q','f','d','I','2I','16s')

def utf(data):
    if len(data)<32 or data[:4]!=b'@UTF':raise ValueError('Invalid UTF header')
    total,version,row_at,strings_at,blob_at,name_at,columns,width,rows=struct.unpack_from('>IHHIIIHHI',data,4)
    total+=8;row_at+=8;strings_at+=8;blob_at+=8
    if version not in (0,1) or total>len(data) or not 32<=row_at<=strings_at<blob_at<=total or columns>1024 or rows>100000 or row_at+rows*width>strings_at:raise ValueError('Invalid UTF table limits')
    def string(offset):
        at=strings_at+offset
        if at<strings_at or at>=blob_at:raise ValueError('Invalid UTF string offset')
        end=data.find(b'\0',at,blob_at)
        if end<0:raise ValueError('Unterminated UTF string')
        return data[at:end].decode('utf-8')
    def value(kind,at,limit):
        if kind>=len(FORMATS):raise ValueError('Unknown UTF value type')
        size=struct.calcsize('>'+FORMATS[kind])
        if at<0 or at+size>limit:raise ValueError('Truncated UTF value')
        values=struct.unpack_from('>'+FORMATS[kind],data,at)
        if kind==10:return string(values[0]),size
        if kind==11:
            offset,length=values
            if blob_at+offset>total or length>total-blob_at-offset:raise ValueError('UTF blob outside table')
            return data[blob_at+offset:blob_at+offset+length],size
        return values[0],size
    schema=[];at=32;row_offset=0
    for _ in range(columns):
        if at+5>row_at:raise ValueError('Truncated UTF schema')
        info,name=struct.unpack_from('>BI',data,at);at+=5;flags,kind=info&240,info&15
        if flags not in (16,48,80) or kind>=len(FORMATS):raise ValueError('Unsupported UTF column')
        size=struct.calcsize('>'+FORMATS[kind]);constant=None
        if flags==48:constant,used=value(kind,at,row_at);at+=used
        if flags==80:
            location=row_offset;row_offset+=size
        else:location=-1
        schema.append((string(name),kind,location,constant))
    if row_offset!=width:raise ValueError('UTF row width does not match schema')
    result=[]
    for row in range(rows):
        record={}
        for name,kind,offset,constant in schema:
            record[name]=value(kind,row_at+row*width+offset,row_at+(row+1)*width)[0] if offset>=0 else constant
        result.append(record)
    return string(name_at),result

def awb(data):
    if len(data)<16 or data[:4]!=b'AFS2':raise ValueError('Invalid AFS2 header')
    offset_width,id_width=data[5],struct.unpack_from('<H',data,6)[0]
    count,alignment,subkey=struct.unpack_from('<IHH',data,8)
    if offset_width not in (2,4) or id_width!=2 or not 0<alignment<=4096 or count>10000:raise ValueError('Unsupported AFS2 layout')
    table=16+count*id_width
    if table+(count+1)*offset_width>len(data):raise ValueError('Truncated AFS2 directory')
    seen=set()
    offsets=[int.from_bytes(data[table+i*offset_width:table+(i+1)*offset_width],'little') for i in range(count+1)];result=[]
    for i in range(count):
        begin=(offsets[i]+alignment-1)//alignment*alignment;end=offsets[i+1]
        if begin<table+(count+1)*offset_width or begin>end or end>len(data):raise ValueError('AFS2 member outside bank')
        ident=struct.unpack_from('<H',data,16+i*2)[0]
        if ident in seen:raise ValueError('Duplicate AFS2 wave ID')
        seen.add(ident);result.append((ident,data[begin:end]))
    return subkey,result
