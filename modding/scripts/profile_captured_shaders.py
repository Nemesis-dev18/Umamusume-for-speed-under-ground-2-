"""Prove direct v0-to-clip matrix rows in captured VS1.1 programs; never read executables."""
import hashlib
import json
import struct
from inspect_assets import ROOT

LENGTHS={0:0,1:2,2:3,3:3,4:4,5:3,6:2,7:2,8:3,9:3,10:3,11:3,12:3,13:3,14:2,15:2,16:2,17:3,18:4,19:2,20:3,21:3,22:3,23:3,24:3,31:2,78:2,79:2,81:5}

def matrix_rows(words):
    if not words or words[0]!=0xfffe0101:raise ValueError('Only observed VS1.1 is supported')
    registers={};defined=set();at=1;ended=False
    def key(token):return ((token>>28)&7)|((token>>8)&24),token&2047
    def source(token):
        kind,index=key(token)
        if token&0x2000:return [None]*4
        values=registers.get((kind,index))
        if values is None:
            values=[('input',index,k) for k in range(4)] if kind==1 else [('constant',index,k,1) for k in range(4)] if kind==2 else [None]*4
        result=[values[(token>>(16+2*k))&3] for k in range(4)]
        modifier=(token>>24)&15
        if modifier==1:
            result=[v[:-1]+(-v[-1],) if v and v[0] in ('dot','constant') else None for v in result]
        elif modifier:result=[None]*4
        return result
    while at<len(words):
        instruction=words[at];at+=1;op=instruction&65535
        if op==65535:
            if instruction!=65535 or at!=len(words):raise ValueError('Invalid END')
            ended=True;break
        if op==65534:
            count=(instruction>>16)&32767
            if at+count>len(words):raise ValueError('Truncated comment')
            at+=count;continue
        if op not in LENGTHS or instruction!=op:raise ValueError('Unsupported instruction/flags')
        count=LENGTHS[op]
        if at+count>len(words):raise ValueError('Truncated operands')
        args=words[at:at+count];at+=count
        if not count or op==31:continue
        destination=args[0];kind,index=key(destination);mask=(destination>>16)&15;value=[None]*4
        if op==81:defined.add(index)
        elif op==1:value=source(args[1])
        elif op in (9,20):
            position=source(args[1]);constant=source(args[2])
            if position==[('input',0,k) for k in range(4)] and constant[0] is not None:
                register=constant[0][1];sign=constant[0][-1]
                if constant==[('constant',register,k,sign) for k in range(4)]:
                    value=[('dot',register+(k if op==20 else 0),sign) for k in range(4)]
        if destination&0x0ff00000:value=[None]*4
        prior=registers.get((kind,index),[None]*4).copy()
        for k in range(4):
            if mask&(1<<k):prior[k]=value[k]
        registers[(kind,index)]=prior
    if not ended:raise ValueError('Missing END')
    result=registers.get((4,0),[None]*4)
    if any(v is None or v[0]!='dot' or v[1] in defined for v in result):raise ValueError('Position is not a direct input matrix transform')
    return [(v[1],v[2]) for v in result]


def shader_metadata(words):
    table={};colored=False;at=1;uv_input=None;uv_output=-1
    while at<len(words):
        token=words[at];at+=1;op=token&65535
        if op==65535:break
        if op==65534:
            count=(token>>16)&32767
            if at+count>len(words):raise ValueError('Truncated metadata comment')
            comment=struct.pack(f'<{count}I',*words[at:at+count]);at+=count
            if comment[:4]!=b'CTAB':continue
            data=comment[4:]
            if len(data)<28:raise ValueError('Short CTAB')
            size,creator,version,number,info,flags,target=struct.unpack_from('<7I',data)
            if size!=28 or number>256 or info+number*20>len(data):raise ValueError('Invalid CTAB directory')
            for i in range(number):
                name,kind,register,n,res,typ,default=struct.unpack_from('<I4H2I',data,info+20*i)
                end=data.find(b'\0',name)
                if name>=len(data) or end<name or end-name>256:raise ValueError('Invalid constant name')
                if kind==2 and register+n<=256:table[data[name:end].decode('ascii')]=(register,n)
            continue
        if op not in LENGTHS or at+LENGTHS[op]>len(words):raise ValueError('Invalid metadata instruction')
        args=words[at:at+LENGTHS[op]];at+=LENGTHS[op]
        if op==31 and args[0]&0xf001f==10 and args[1]==0x900f0001:colored=True
        if op==31 and args[0]&0xf001f==5:uv_input=args[1]&2047
        if op==1 and uv_input is not None and args[1]==0x90e40000+uv_input and args[0]&0xf0001800==0xe0000000 and args[0]&0x30000==0x30000:uv_output=args[0]&2047
    worldview=table.get('WorldView')
    return (worldview[0] if worldview and worldview[1]==3 else -1),colored,uv_output


def main():
    path=ROOT/'modding/diagnostics/game-pipeline-session-1.log';raw=path.read_bytes();profiles=[];report=[]
    for line in raw.decode().splitlines():
        if not line.startswith('VS '):continue
        head,tokens=line.split('words=');words=[int(t,16) for t in tokens.split()];ident=int(head.split('id=')[1].split()[0]);data=struct.pack(f'<{len(words)}I',*words)
        entry={'id':ident,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        try:
            rows=matrix_rows(words);wv,colored,uv=shader_metadata(words);profiles.append((ident,words,rows,wv,colored,uv));entry.update(rows=rows,worldview_register=wv,color_input_reference_candidate=colored,uv_output=uv)
        except ValueError as error:entry['unsupported_reason']=str(error)
        report.append(entry)
    lines=['/* Generated from explicitly captured GPU shader objects, not SPEED2.EXE. */','#ifndef UMA_SHADER_PROFILES_H','#define UMA_SHADER_PROFILES_H','typedef struct {const DWORD *words;UINT bytes;UINT rows[4];float signs[4];int worldview;BOOL reference_candidate;int uv_output;} UmaShaderProfile;']
    for ident,words,rows,wv,colored,uv in profiles:lines.append(f'static const DWORD uma_vs_{ident}[]={{'+','.join(hex(w) for w in words)+'};')
    lines.append('static const UmaShaderProfile uma_shader_profiles[]={')
    for ident,words,rows,wv,colored,uv in profiles:lines.append('{uma_vs_%d,sizeof(uma_vs_%d),{%s},{%s},%d,%d,%d},'%(ident,ident,','.join(str(r) for r,s in rows),','.join(str(s) for r,s in rows),wv,int(colored),uv))
    lines+=['};','#define UMA_SHADER_PROFILE_COUNT (sizeof(uma_shader_profiles)/sizeof(uma_shader_profiles[0]))','#endif','']
    (ROOT/'modding/runtime/uma_shader_profiles.h').write_text('\n'.join(lines))
    (ROOT/'modding/diagnostics/shader-profile-analysis.json').write_text(json.dumps({'source_sha256':hashlib.sha256(raw).hexdigest(),'programs':report,'exact_bytecode_match_required':True,'game_integration_verified':False},indent=2)+'\n')
    print('Proved direct position transforms:',[(i,r,wv,c) for i,w,r,wv,c,uv in profiles]);print('Rejected:',[r['id'] for r in report if 'unsupported_reason' in r])

if __name__=='__main__':main()
