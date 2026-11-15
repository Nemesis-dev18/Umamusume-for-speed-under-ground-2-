"""Read only the embedded EA sample-bank region; leave AEMS program bytes opaque."""
import struct

def patch(data,at,limit):
    if at<0 or at+4>limit or data[at:at+2]!=b'PT':raise ValueError('Invalid EA patch header')
    platform=struct.unpack_from('<H',data,at+2)[0];at+=4;tags={}
    for _ in range(256):
        if at>=limit:raise ValueError('Truncated EA patch')
        tag=data[at];at+=1
        if tag in (254,255):return {'platform':platform,'tags':tags,'end':at}
        if tag in (252,253):continue
        if at>=limit:raise ValueError('Truncated EA tag length')
        size=data[at];at+=1
        if size==255:
            if at+4>limit:raise ValueError('Truncated EA blob length')
            size=int.from_bytes(data[at:at+4],'big');at+=4
        if size>limit-at:raise ValueError('EA tag outside sample bank')
        tags[tag]=int.from_bytes(data[at:at+size],'big') if size<=4 else None;at+=size
    raise ValueError('Too many EA patch tags')

def abk_samples(data):
    if len(data)<64 or data[:4]!=b'ABKC':raise ValueError('Invalid ABKC header')
    base,size=struct.unpack_from('<2I',data,32)
    if base<64 or size<20 or base+size>len(data) or data[base:base+4]!=b'BNKl':raise ValueError('Invalid embedded BNKl bounds')
    version=data[base+4];count=struct.unpack_from('<H',data,base+6)[0]
    if version not in (4,5) or count>1024 or 20+count*4>size:raise ValueError('Unsupported BNKl directory')
    result=[]
    for index in range(count):
        entry=base+20+index*4;relative=struct.unpack_from('<i',data,entry)[0]
        if not relative:continue
        address=entry+relative
        if address<base+20+count*4:raise ValueError('Patch overlaps bank directory')
        item=patch(data,address,base+size);item.update(index=index,bank_base=base,bank_end=base+size);result.append(item)
    return result
