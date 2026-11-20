"""Stage native-resolution diffuse atlases while preserving installed animated rigs."""
import hashlib,json,struct
from pathlib import Path
from pack_steam_atlas import pack,ROOT

def main():
 rows=[]
 for char in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
  identifier=char['id'];folder=ROOT/'modding/uma-steam/fleet'/str(identifier);out=ROOT/'modding/staged-runtime/fleet-detail'/str(identifier)
  pack(folder,output=out,preserve_resolution=True)
  before=(ROOT/'modding/runtime/fleet'/str(identifier)/'model.umab').read_bytes();uv_asset=(out/'model-atlas.umab').read_bytes();after=bytearray(before)
  nv=struct.unpack_from('<I',before,8)[0]
  if nv!=struct.unpack_from('<I',uv_asset,8)[0]:raise ValueError('Vertex order/count changed')
  for i in range(nv):
   at=40+i*36
   if before[at:at+28]!=uv_asset[at:at+28]:raise ValueError('Rest mesh changed during atlas staging')
   after[at+28:at+36]=uv_asset[at+28:at+36]
  if after[40+nv*36:]!=before[40+nv*36:]:raise ValueError('Rig, skin or animation changed')
  (out/'model.umab').write_bytes(after);report=json.loads((out/'atlas.json').read_text());report['installed_rig_preserved']=True;report['installed_baseline_sha256']=hashlib.sha256(before).hexdigest();report['model_sha256']=hashlib.sha256(after).hexdigest();(out/'detail.json').write_text(json.dumps(report,indent=2)+'\n');rows.append({'id':identifier,'slot':char['nfs_slot'],'folder':str(out.relative_to(ROOT)),'vertices':nv,'bones':struct.unpack_from('<I',after,16)[0],'atlas_bytes':(out/'atlas.dds').stat().st_size,'model_sha256':report['model_sha256'],'atlas_sha256':report['atlas_sha256']});print(identifier,'full-resolution textures; existing rig preserved',flush=True)
 (ROOT/'modding/detail-atlas-plan.json').write_text(json.dumps({'characters':rows,'installed':False,'gameplay_verified':False,'scope':'Native source diffuse resolution preserved; does not recreate Unity toon shader or add geometric detail'},indent=2)+'\n')
if __name__=='__main__':main()
