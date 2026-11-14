"""Render the authored motion with a CPU rasterizer; not an in-game capture."""
import argparse
from pathlib import Path
import struct
import numpy as np
from PIL import Image,ImageDraw
from inspect_assets import ROOT
from animate_kitasan import Rig
rig=Rig();raw=(ROOT/'modding/character-source/mesh.bin').read_bytes()
nv,ni=struct.unpack_from('<II',raw)
uv=rig.records[:,6:8]
col=np.ndarray((nv,4),'u1',raw,40,strides=(36,1))/255
faces=np.frombuffer(raw,'<u4',ni,8+nv*36).reshape(-1,3)
tex=np.array(Image.open(ROOT/'modding/character-source/atlas.png').convert('RGBA'))
def basis(eye):
 forward=np.array([0.,0.,1.05])-eye;forward/=np.linalg.norm(forward)
 right=np.cross(forward,[0,0,1]);assert np.linalg.norm(right)>0.1;right/=np.linalg.norm(right)
 return right,np.cross(right,forward),forward

def render(eye):
 w,h=320,480;right,up,forward=basis(np.array(eye));center=np.array([0,0,1.05]);scale=190
 xy=np.column_stack(((p-center)@right*scale+w/2,h/2-(p-center)@up*scale));z=(p-np.array(eye))@forward
 canvas=np.full((h,w,3),[37,42,50],dtype='u1');depth=np.full((h,w),np.inf)
 light=np.array([1,2,3.]);light/=np.linalg.norm(light)
 for ix in faces:
  a=xy[ix];lo=np.maximum(np.floor(a.min(0)).astype(int),[0,0]);hi=np.minimum(np.ceil(a.max(0)).astype(int),[w-1,h-1])
  if (hi<lo).any():continue
  x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
  den=(a[1,1]-a[2,1])*(a[0,0]-a[2,0])+(a[2,0]-a[1,0])*(a[0,1]-a[2,1])
  if abs(den)<1e-7:continue
  u=((a[1,1]-a[2,1])*(x-a[2,0])+(a[2,0]-a[1,0])*(y-a[2,1]))/den
  t=((a[2,1]-a[0,1])*(x-a[2,0])+(a[0,0]-a[2,0])*(y-a[2,1]))/den;q=1-u-t
  weights=np.stack((u,t,q),-1);zz=weights@z[ix]
  region=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];mask=(u>=0)&(t>=0)&(q>=0)&(zz<region)
  if not mask.any():continue
  coords=np.clip((weights@uv[ix]*(tex.shape[1]-1)).astype(int),0,tex.shape[1]-1);pixels=tex[coords[:,:,1],coords[:,:,0]]/255
  colours=weights@col[ix];mask&=pixels[:,:,3]*colours[:,:,3]>.5
  n=weights@norm[ix];n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-8)
  shade=.65+.35*np.maximum(0,n@light)
  rgb=np.clip(pixels[:,:,:3]*colours[:,:,:3]*shade[:,:,None]*255,0,255).astype('u1')
  canvas[lo[1]:hi[1]+1,lo[0]:hi[0]+1][mask]=rgb[mask];region[mask]=zz[mask]
 return Image.fromarray(canvas)

def frame_image(phase,amount,label):
 global p,norm
 rotation,offset,_,_=rig.pose(phase,amount);p,norm=rig.skin(rotation,offset)
 image=Image.new('RGB',(640,525),(24,28,34));image.paste(render([3,2,1.8]),(0,30));image.paste(render([-3,-2,1.8]),(320,30))
 draw=ImageDraw.Draw(image);draw.text((10,10),'PREVIA OFFLINE — NO ES GAMEPLAY',fill='white');draw.text((10,507),label,fill='white')
 return image
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='animation-offline')
 args=parser.parse_args();relative=Path(args.output)
 if relative.is_absolute() or '..' in relative.parts:raise ValueError('Output must stay in modding')
 out=ROOT/'modding'/relative
 if not out.is_dir() or out.is_symlink():raise ValueError('Expected existing offline clip directory')
 frame_image(0,0,'Reposo propuesto | integracion en juego pendiente').save(out/'idle-preview.png')
 frames=[]
 for i in range(10):
  frames.append(frame_image(i/10,1,'Carrera propuesta | IK de pies | integracion en juego pendiente'))
  print('Rendered offline frame',i+1,flush=True)
 frames[0].save(out/'run-preview.gif',save_all=True,append_images=frames[1:],duration=55,loop=0,optimize=False)

if __name__=='__main__':main()
