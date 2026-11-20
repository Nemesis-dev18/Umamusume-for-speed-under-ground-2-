"""Stage all 350Z kits/LODs as Gentildonna carriers; no game installation."""
import hashlib,json,struct,subprocess
import numpy as np
from inspect_assets import ROOT,cartypes,chunks,flatten
from extract_assets import payload,skip_words
from fleet_carrier import carrier
from prepare_steam_fleet_geometry import verify,RLIB
from prepare_character_collision import prepare as collision,LOWER,UPPER
from disable_car_effects import NAMES,rename_markers,string_hash


def main():
 slot='350Z';identifier=9001;folder=ROOT/'modding/staged-runtime/fleet'/str(identifier);folder.mkdir(parents=True,exist_ok=True)
 (folder/'carrier.bin').write_bytes(carrier(identifier));raw=(ROOT/'CARS/350Z/GEOMETRY.BIN').read_bytes();positions={0x9b971511:[],0x0ee87ec4:[]}
 for node in flatten(chunks(raw)):
  if node['id']=='0x0013401a':
   data=payload(raw,node)
   for at in range(skip_words(data),len(data),80):
    key=struct.unpack_from('<I',data,at)[0]
    if key in positions:positions[key].append(struct.unpack_from('<3f',data,at+64))
 sides=[]
 for group in positions.values():
  assert group and np.allclose(group,group[0]);sides.append(group[0])
 car=next(c for c in cartypes((ROOT/'GLOBAL/GLOBALB.BUN').read_bytes()) if c['name']==slot)
 wheels=[[w['longitudinal'],w['lateral'],w['height']] for w in car['wheels']];(folder/'anchors.bin').write_bytes(np.array([*wheels,*sides],dtype='<f4').tobytes())
 model=ROOT/'modding/staged-runtime/gentildonna/model.umab'
 sampled=subprocess.run([str(ROOT/'modding/runtime/test-build/fleet-bounds'),str(model)],check=True,capture_output=True);assert len(sampled.stdout)==24;(folder/'bounds.bin').write_bytes(sampled.stdout)
 assert hashlib.sha256(RLIB.read_bytes()).hexdigest()=='03a5461701f4f86a251cba6e0e0725d504cfd4ef8ee50bd236af0282e9c4aa0f'
 subprocess.run(['rustc','--edition=2021','-O',str(ROOT/'modding/runtime/prepare_fleet_geometry.rs'),'--extern',f'gizmo_nfs={RLIB}','-L',f'dependency={RLIB.parent}','-o',str(ROOT/'modding/runtime/prepare-fleet-geometry')],check=True)
 built=subprocess.run([str(ROOT/'modding/runtime/prepare-fleet-geometry'),slot,str(identifier)],check=True,capture_output=True);candidate=built.stdout
 report=verify(raw,candidate,carrier(identifier),sampled.stdout,slot);candidate,hulls,ranges=collision(candidate,slot,LOWER*(1.78/1.95),UPPER*(1.78/1.95))
 hashes=set()
 for node in flatten(chunks(candidate)):
  if node['id']=='0x0013401a':
   data=payload(candidate,node);hashes.update(struct.unpack_from('<I',data,at)[0] for at in range(skip_words(data),len(data),80))
 candidate,markers=rename_markers(candidate,[name for name in (*NAMES,'CENTRE_HEADLIGHT') if string_hash(name) in hashes],())
 assert (ROOT/'CARS/350Z/GEOMETRY.BIN').read_bytes()==raw
 (folder/'GEOMETRY.BIN').write_bytes(candidate)
 (folder/'geometry.json').write_text(json.dumps({'slot':slot,'local_identifier':identifier,'verification':report,'hulls':hulls,'disabled_markers':markers,'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'installed':False},indent=2)+'\n');print(report)

if __name__=='__main__':main()
