"""Stage only the Miata/Tachyon static unlock prerequisite; never edit saves."""
import hashlib,json,struct
from inspect_assets import ROOT,chunks,flatten,jdlz
from extract_assets import payload
from disable_car_effects import string_hash
from prepare_tiremask import rewrite_jdlz


def prepare(source):
    packed=source.startswith(b'JDLZ');raw=jdlz(source) if packed else source;matches=[]
    for node in flatten(chunks(raw)):
        if node['id']!='0x00034a1f':continue
        data=payload(raw,node)
        if len(data)%12:raise ValueError('Partial car unlock record')
        for at in range(0,len(data),12):
            key,first,second=struct.unpack_from('<3I',data,at)
            if key==string_hash('MIATA'):matches.append((node['payload']+at,first,second))
    if len(matches)!=1 or matches[0][1:]!=(0,0x1185ef07):raise ValueError('Unexpected Miata prerequisites; refusing change')
    record,first,second=matches[0];at=record+8;out=bytearray(raw);struct.pack_into('<I',out,at,0)
    if raw[:at]!=out[:at] or raw[at+4:]!=out[at+4:]:raise ValueError('Unrelated global bytes changed')
    encoded=rewrite_jdlz(source,bytes(out)) if packed else bytes(out)
    if (jdlz(encoded) if packed else encoded)!=out:raise ValueError('Global roundtrip mismatch')
    return encoded,{'decoded_offset':at,'bytes':4,'before':hex(second),'after':'0x0','car':'MIATA','character':'Agnes Tachyon','unrelated_decoded_bytes_unchanged':True}


def main():
    rows=[]
    for name in ['GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc']:
        source=(ROOT/name).read_bytes();data,field=prepare(source);candidate=ROOT/'modding/staged-runtime'/('tachyon-unlock-'+name.split('/')[-1]);candidate.write_bytes(data)
        rows.append({'target':name,'candidate':str(candidate.relative_to(ROOT)),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'field':field})
    (ROOT/'modding/tachyon-unlock-plan.json').write_text(json.dumps({'files':rows,'installed':False,'save_files_touched':False,'menu_verified':False},indent=2)+'\n')
    print('Two global variants staged; only four decoded bytes each; menu availability not yet verified')

if __name__=='__main__':main()
