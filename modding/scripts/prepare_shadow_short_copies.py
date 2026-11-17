"""Stage short-copy JDLZ shadows without adding compressed-stream tail padding."""
import hashlib,json,struct
from pathlib import Path
from inspect_assets import ROOT,jdlz
from prepare_shadow_guard import descriptors
from prepare_tiremask import rewrite_jdlz
from disable_car_effects import string_hash
from verify_foot_shadow import verify


def prepare(original,compact,slot):
    before,after=descriptors(original),descriptors(compact);out=bytearray(original);streams=[]
    for suffix in ('FE','IG'):
        key=string_hash(slot+'_SHADOW'+suffix);at,a=before[key];_,b=after[key]
        if a[1]!=b[1] or a[3:]!=b[3:]:raise ValueError('Relocated shadow unsupported')
        packed=compact[b[1]:b[1]+b[2]];decoded=jdlz(packed)
        encoded=rewrite_jdlz(packed,decoded,max_copy=512)
        if len(encoded)>a[2]:raise ValueError('Short-copy stream exceeds original slot')
        out[a[1]:a[1]+len(encoded)]=encoded;struct.pack_into('<I',out,at+8,len(encoded))
        if jdlz(encoded)!=decoded:raise ValueError('Short-copy roundtrip mismatch')
        streams.append({'hash':hex(key),'original_bytes':a[2],'short_copy_bytes':len(encoded)})
    verify(original,bytes(out),slot)
    return bytes(out),streams


def main():
    rows=[]
    for row in json.loads((ROOT/'modding/fleet-shadow-plan.json').read_text())['files']:
        original=(ROOT/(row['target']+'.before-shadow-guard.bak')).read_bytes();compact=(ROOT/row['candidate']).read_bytes()
        data,streams=prepare(original,compact,row['slot']);out=ROOT/'modding/staged-runtime/fleet-shadows-short-copy'/row['slot']/'TEXTURES.BIN'
        out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
        rows.append({'target':row['target'],'slot':row['slot'],'candidate':str(out.relative_to(ROOT)),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'streams':streams})
    (ROOT/'modding/fleet-shadow-short-copy-plan.json').write_text(json.dumps({'files':rows,'installed':False,'game_verified':False,'maximum_copy_length':512,'compressed_tail_padding_added':False},indent=2)+'\n')
    print('Seven short-copy candidates staged; no relocation, no compressed tail padding; not game verified')

if __name__=='__main__':main()
