import hashlib,json,struct,sys,unittest
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/scripts'))
from bake_steam_eyes import barycentric,sample


class FleetMaterials(unittest.TestCase):
    def test_projection_and_filter(self):
        triangle=np.array([[0.,0.],[2.,0.],[0.,2.]])
        np.testing.assert_allclose(barycentric(np.array([[.5,.5],[2,2]]),triangle),[[.5,.25,.25],[-1,1,1]])
        self.assertIsNone(barycentric(np.array([[0,0]]),np.zeros((3,2))))
        image=np.arange(16).reshape(2,2,4).astype(float)
        np.testing.assert_allclose(sample(image,np.array([[.5,.5],[0,0],[1,1]])),[image.mean((0,1)),image[0,0],image[1,1]])

    def test_atlas_changes_only_uv_and_neutral_effect_indices(self):
        for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
            with self.subTest(character=c['name']):
                folder=ROOT/'modding/uma-steam/fleet'/str(c['id']);runtime=folder/'runtime';report=json.loads((runtime/'model.json').read_text());atlas=json.loads((runtime/'atlas.json').read_text());base=(runtime/'model.umab').read_bytes();packed=(runtime/'model-atlas.umab').read_bytes();dds=(runtime/'atlas.dds').read_bytes()
                self.assertEqual(len(base),len(packed));self.assertEqual(hashlib.sha256(packed).hexdigest(),atlas['model_sha256']);self.assertEqual(hashlib.sha256(dds).hexdigest(),atlas['atlas_sha256'])
                self.assertEqual(dds[:4],b'DDS ');self.assertEqual(dds[84:88],b'DXT5');self.assertEqual(struct.unpack_from('<I',dds,28)[0],12);self.assertEqual(len(dds),128+sum(l['bytes'] for l in atlas['levels']));self.assertTrue(atlas['neutral_iris_baked'])
                nv,ni,nb=struct.unpack_from('<III',base,8);permitted=np.zeros(len(base),bool)
                self.assertEqual(struct.unpack_from('<I',base,4)[0],3)
                for v in range(nv):permitted[40+v*36+28:40+(v+1)*36]=True
                index_offset=40+nv*60+nb*16
                for group in report['groups']:
                    if group['eye_depth_off'] or group['material'].endswith('_cheek'):
                        first=index_offset+group['first_index']*2;length=group['index_count']*2;permitted[first:first+length]=True;self.assertEqual(packed[first:first+length],bytes(length))
                before=np.frombuffer(base,'u1');after=np.frombuffer(packed,'u1');self.assertFalse(np.any((before!=after)&~permitted))
                uv=np.ndarray((nv,2),'<f4',packed,offset=68,strides=(36,4));self.assertGreater(float(uv.min()),0);self.assertLess(float(uv.max()),1)
                cells=list(atlas['layout'].values())
                for i,cell in enumerate(cells):
                    x,y,w,h=cell['cell'];self.assertLessEqual(x+w,2048);self.assertLessEqual(y+h,2048)
                    for other in cells[i+1:]:
                        a,b,cw,ch=other['cell'];self.assertTrue(x+w<=a or a+cw<=x or y+h<=b or b+ch<=y)
                g=json.loads((folder/'source.gltf').read_text());face=next(m for m in g['materials'] if m['name'].endswith('_face'));texture=face['pbrMetallicRoughness']['baseColorTexture']['index'];original=np.array(Image.open(folder/g['images'][g['textures'][texture]['source']]['uri']).convert('RGBA'));baked=np.array(Image.open(runtime/'face-baked.png'))
                np.testing.assert_array_equal(original[:,:,3],baked[:,:,3]);changed=np.any(original[:,:,:3]!=baked[:,:,:3],axis=2);self.assertGreater(int(changed.sum()),50);self.assertLess(int(changed.sum()),original.shape[0]*original.shape[1]*.2)
                review=json.loads((folder/'review-eyes.gltf').read_text())
                self.assertFalse(any(review['materials'][p['material']]['name'].endswith(('_eye','_cheek')) for m in review['meshes'] for p in m['primitives']))

if __name__=='__main__':unittest.main()
