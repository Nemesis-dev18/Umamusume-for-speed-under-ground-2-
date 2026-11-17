"""Validate the observed NFSU2 end-of-token flag refill contract without executing game code."""
import struct
from inspect_assets import jdlz


def validate_native(data):
    if len(data)<18 or data[:8]!=b'JDLZ\x02\x10\0\0':raise ValueError('Invalid native JDLZ header')
    size,compressed=struct.unpack_from('<II',data,8)
    if not 0<size<=256*1024*1024 or not 18<=compressed<=len(data):raise ValueError('Invalid native JDLZ bounds')
    at=18;remaining=compressed-18;first=data[16]|256;second=data[17]|256;output=bytearray()
    def read():
        nonlocal at,remaining
        if remaining<=0 or at>=compressed:raise ValueError('Native flag/token read crosses compressed boundary')
        value=data[at];at+=1;remaining-=1;return value
    while remaining:
        if first&1:
            a,b=read(),read()
            length,distance=(((a&240)<<4|b)+3,(a&15)+1) if second&1 else ((a&31)+3,(b|(a&224)<<3)+17)
            if distance>len(output) or len(output)+length>size:raise ValueError('Native copy crosses output boundary')
            for _ in range(length):output.append(output[-distance])
            second>>=1
        else:
            if len(output)<size:output.append(read())
            else:remaining-=1
        first>>=1
        if first==1:first=read()|256
        if second==1:second=read()|256
    if len(output)!=size:raise ValueError('Native output is incomplete')
    return bytes(output)


def finish_native(data):
    decoded=jdlz(data);at=16;first=second=1;position=0
    while position<len(decoded):
        if first==1:first=data[at]|256;at+=1
        if second==1:second=data[at]|256;at+=1
        if first&1:
            a,b=data[at:at+2];at+=2
            position+=(((a&240)<<4|b)+3) if second&1 else ((a&31)+3)
            second>>=1
        else:position+=1;at+=1
        first>>=1
    result=bytearray(data[:at]);result.extend(bytes((first==1)+(second==1)))
    struct.pack_into('<I',result,12,len(result))
    if validate_native(result)!=decoded:raise ValueError('Native finalization changed output')
    return bytes(result)
