"""Stage compact shadows with the observed native JDLZ terminal flag refills."""
import hashlib,json,struct
from inspect_assets import ROOT
from prepare_shadow_guard import descriptors
from disable_car_effects import string_hash
from jdlz_native import finish_native,validate_native
from verify_foot_shadow import verify


def main():
    rows=[]
    for row in json.loads((ROOT/'modding/fleet-shadow-plan.json').read_text())['files']:
        original=(ROOT/(row['target']+'.before-shadow-guard.bak')).read_bytes();compact=(ROOT/row['candidate']).read_bytes()
        old,new=descriptors(original),descriptors(compact);out=bytearray(original);streams=[]
        for suffix in ('FE','IG'):
            key=string_hash(row['slot']+'_SHADOW'+suffix);at,a=old[key];_,b=new[key]
            if a[1]!=b[1] or a[3:]!=b[3:]:raise ValueError('Unexpected relocation or metadata change')
            encoded=finish_native(compact[b[1]:b[1]+b[2]])
            if len(encoded)>a[2]:raise ValueError('Native stream exceeds original slot')
            out[a[1]:a[1]+len(encoded)]=encoded;struct.pack_into('<I',out,at+8,len(encoded))
            validate_native(encoded);streams.append({'hash':hex(key),'compressed_bytes':len(encoded),'native_contract_checked':True})
        result=verify(original,bytes(out),row['slot']);dest=ROOT/'modding/staged-runtime/fleet-shadows-native'/row['slot']/'TEXTURES.BIN';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out)
        rows.append({'target':row['target'],'slot':row['slot'],'candidate':str(dest.relative_to(ROOT)),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(out).hexdigest(),'streams':streams,'verification':result})
    (ROOT/'modding/native-shadow-plan.json').write_text(json.dumps({'files':rows,'installed':False,'game_verified':False,'contract_source':'Read-only observed runtime instructions; safe Python reconstruction'},indent=2)+'\n')
    print('Seven compact native-contract shadow packages staged; game verification pending')

if __name__=='__main__':main()
