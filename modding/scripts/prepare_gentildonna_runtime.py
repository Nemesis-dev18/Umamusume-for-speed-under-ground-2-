"""Bake Gentildonna's permitted native mesh and original race cycle into staging."""
import json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from inspect_assets import ROOT
from animate_kitasan import Rig
from retarget_uma_motion import UmaRetarget
from pack_motion import pack
from pack_texture import pack_texture
from verify_gentildonna_source import verify


def main():
 model,validation=verify();source=ROOT/'modding/staged-runtime/gentildonna-source';out=ROOT/'modding/staged-runtime/gentildonna';out.mkdir(exist_ok=True)
 rig=Rig(source);motion=UmaRetarget(target=rig)
 for name,amount,count in [('idle',0,32),('run',1,48)]:
  rotations=[];offsets=[]
  for frame in range(count):
   r,t,_,_=motion.pose(frame/count,amount);p,n=rig.skin(r,t)
   assert np.isfinite(p).all() and np.isfinite(n).all() and np.max(abs(np.linalg.det(r)-1))<1e-5
   assert np.max(abs(p))<4
   rotations.append(r.astype('<f4'));offsets.append(t.astype('<f4'))
  np.savez_compressed(out/(name+'.npz'),rotations=np.array(rotations),offsets=np.array(offsets))
 raw=bytearray(pack(out,source));struct.pack_into('<I',raw,4,3);raw=raw[:32]+struct.pack('<2f',2.,motion.clip.duration)+raw[32:];(out/'model.umab').write_bytes(raw)
 # Keep each source image separate: wrapping UVs cannot be placed in a clamped atlas.
 textures=[]
 for i,texture in enumerate(model.textures):
  path=Path(texture.path);path=path if path.is_absolute() else ROOT/path
  with Image.open(path) as im:encoded,levels,error=pack_texture(im)
  (out/f'material-{i:02}.dds').write_bytes(encoded);textures.append({'index':i,'source':str(path.relative_to(ROOT)),'levels':levels,'rgb_rmse':error})
 (out/'atlas.dds').write_bytes((out/'material-00.dds').read_bytes())
 hidden={'特殊瞳','動的ハイライト','涙','青影','紅頬','汗','フェイシャル表情'}
 batches=[];first=0
 for material in model.materials:
  assert 0<=material.texture<len(textures)
  batches.append((first,material.vertex_count,material.texture,int(material.name not in hidden)))
  first+=material.vertex_count
 (out/'materials.bin').write_bytes(struct.pack('<4s3I',b'UMAM',1,len(batches),len(textures))+b''.join(struct.pack('<4I',*batch) for batch in batches))
 report={'installed':False,'source':validation['source_sha256'],'vertices':len(model.vertices),'triangles':len(model.faces),'native_materials':len(batches),'textures':textures,'run_duration':motion.clip.duration,'neutral_hidden_materials':sorted(hidden),'limitations':['Original MMD shader effects not reproduced','Secondary clothing not integrated yet']}
 (out/'runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS staged Gentildonna motion and native-resolution material textures',flush=True)

if __name__=='__main__':main()
