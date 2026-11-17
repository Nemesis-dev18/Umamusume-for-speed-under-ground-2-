"""Bake the neutral iris overlay into face UVs, so ordinary depth testing stays correct."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pack_steam_fleet import NativeSkin
ROOT=Path(__file__).resolve().parents[2]


def barycentric(points,triangle):
    a,b,c=triangle;matrix=np.column_stack((b-a,c-a));det=np.linalg.det(matrix)
    if abs(det)<1e-14:return None
    bc=(points-a)@np.linalg.inv(matrix).T;return np.column_stack((1-bc.sum(axis=1),bc))


def sample(image,uv):
    h,w=image.shape[:2];p=np.clip(uv,0,1)*np.array([w,h])-.5;x=np.clip(p[:,0],0,w-1);y=np.clip(p[:,1],0,h-1);x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1);tx=x-x0;ty=y-y0
    return (image[y0,x0]*(1-tx)[:,None]+image[y0,x1]*tx[:,None])*(1-ty)[:,None]+(image[y1,x0]*(1-tx)[:,None]+image[y1,x1]*tx[:,None])*ty[:,None]


def bake(folder):
    source=NativeSkin(folder);parts=list(source.primitives());face=next(p for p in parts if source.g['materials'][p['material']]['name'].endswith('_face'));eye=next(p for p in parts if source.g['materials'][p['material']]['name'].endswith('_eye'))
    def diffuse(part):
        tex=source.g['materials'][part['material']]['pbrMetallicRoughness']['baseColorTexture'];path=folder/source.g['images'][source.g['textures'][tex['index']]['source']]['uri']
        with Image.open(path) as image:pixels=np.array(image.convert('RGBA'),dtype=float)
        transform=tex.get('extensions',{}).get('KHR_texture_transform',{});uv=part['attributes']['TEXCOORD_0']*np.array(transform.get('scale',[1,1]))+np.array(transform.get('offset',[0,0]))
        return pixels,uv
    original,face_uv=diffuse(face);iris,eye_uv=diffuse(eye);height,width=original.shape[:2];output=original.copy();fp,fn=source.deform(face,source.rest);ep,en=source.deform(eye,source.rest);painted=np.zeros((height,width),bool)
    eye_triangles=eye['indices'].reshape(-1,3)
    for tri in face['indices'].reshape(-1,3):
        if fn[tri,2].mean()<.25:continue
        surface=fp[tri,:2];uv=face_uv[tri]*[width,height]-.5
        candidates=[t for t in eye_triangles if np.all(ep[t,:2].max(0)>=surface.min(0)) and np.all(ep[t,:2].min(0)<=surface.max(0))]
        if not candidates:continue
        lo=np.maximum(np.ceil(uv.min(0)).astype(int),0);hi=np.minimum(np.floor(uv.max(0)).astype(int),[width-1,height-1])
        if np.any(hi<lo):continue
        xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));pixels=np.column_stack((xx.reshape(-1),yy.reshape(-1)));bc=barycentric(pixels,uv)
        if bc is None:continue
        mask=np.min(bc,axis=1)>=-1e-6;pixels=pixels[mask];xy=bc[mask]@surface
        for t in candidates:
            eb=barycentric(xy,ep[t,:2])
            if eb is None:continue
            inside=np.min(eb,axis=1)>=-1e-6
            if not np.any(inside):continue
            colors=sample(iris,eb[inside]@eye_uv[t]);px=pixels[inside];alpha=colors[:,3:4]/255;old=original[px[:,1],px[:,0]]
            output[px[:,1],px[:,0],:3]=colors[:,:3]*alpha+old[:,:3]*(1-alpha);painted[px[:,1],px[:,0]]|=colors[:,3]>32
    count=int(painted.sum())
    if count<50 or count>width*height*.2:raise ValueError('Implausible projected iris area')
    destination=folder/'runtime';destination.mkdir(exist_ok=True);Image.fromarray(np.round(output).astype('uint8')).save(destination/'face-baked.png')
    g=source.g;texture=g['materials'][face['material']]['pbrMetallicRoughness']['baseColorTexture']['index'];g['images'][g['textures'][texture]['source']]['uri']='runtime/face-baked.png'
    for mesh in g['meshes']:mesh['primitives']=[p for p in mesh['primitives'] if p['material']!=eye['material'] and not g['materials'][p['material']]['name'].endswith('_cheek')]
    (folder/'review-eyes.gltf').write_text(json.dumps(g)+'\n')
    receipt={'mode':'Neutral iris texture overlay; source geometry and clips unchanged','painted_pixels':count,'face_size':[width,height],'eye_depth_test_disabled':False,'neutral_cheek_effect':0,'game_integrated':False,'expressions_supported':False}
    # shortcut: neutral iris is baked for idle/run; add a material pass when animated eye expressions are required.
    (destination/'eyes.json').write_text(json.dumps(receipt,indent=2)+'\n');print(folder.name,count,flush=True)


def main():
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:bake(ROOT/'modding/uma-steam/fleet'/str(c['id']))

if __name__=='__main__':main()
