"""Stage only the manufacturer identifiers that select each character's chibi badge."""
import hashlib,json
import numpy as np
from inspect_assets import ROOT,cartypes,jdlz
from prepare_fleet_badges import NAMES,directory
from disable_car_effects import string_hash
from prepare_tiremask import rewrite_jdlz


def main():
    badge=json.loads((ROOT/'modding/fleet-badge-plan.json').read_text());frontend=(ROOT/badge['candidate']).read_bytes()
    if hashlib.sha256(frontend).hexdigest()!=badge['after_sha256']:raise ValueError('Badge candidate changed')
    textures=directory(jdlz(frontend));fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters'];files=[]
    for target in ('GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc'):
        original=(ROOT/target).read_bytes();raw=jdlz(original) if original.startswith(b'JDLZ') else original;out=bytearray(raw);cars={c['name']:c for c in cartypes(raw)};mask=np.zeros(len(raw),bool);fields=[]
        for character in fleet:
            name=NAMES[character['id']];key=string_hash('CARSELECT_MANUFACTURER_'+name)
            if key not in textures:raise ValueError('Missing matching frontend badge')
            at=cars[character['nfs_slot']]['offset']+0xc0;value=name.encode('ascii').ljust(16,b'\0')
            if len(value)!=16:raise ValueError('Manufacturer identifier exceeds field')
            old=raw[at:at+16].split(b'\0')[0].decode('ascii')
            if not old or not old.replace('_','').isalnum():raise ValueError('Unexpected manufacturer field')
            out[at:at+16]=value;mask[at:at+16]=True;fields.append({'slot':character['nfs_slot'],'offset':at,'before':old,'after':name,'texture_hash':hex(key)})
        if np.any((np.frombuffer(raw,'u1')!=np.frombuffer(out,'u1'))&~mask):raise ValueError('Unrelated global bytes changed')
        encoded=rewrite_jdlz(original,bytes(out)) if original.startswith(b'JDLZ') else bytes(out)
        if (jdlz(encoded) if encoded.startswith(b'JDLZ') else encoded)!=out:raise ValueError('Global compression mismatch')
        path=ROOT/'modding/staged-runtime'/('fleet-badge-'+target.split('/')[-1]);path.write_bytes(encoded)
        files.append({'target':target,'candidate':str(path.relative_to(ROOT)),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest(),'fields':fields})
    (ROOT/'modding/fleet-badge-mapping-plan.json').write_text(json.dumps({'files':files,'installed':False,'menu_visual_verified':False},indent=2)+'\n');print('Both global variants mapped to seven exact badge hashes; unrelated bytes preserved')

if __name__=='__main__':main()
