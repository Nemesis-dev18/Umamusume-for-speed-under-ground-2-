import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]

class FleetSources(unittest.TestCase):
    def test_seven_distinct_slots_and_native_skin_buffers(self):
        fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']
        self.assertEqual({c['id'] for c in fleet},{1068,1052,1032,1062,1015,1006,1058})
        self.assertEqual(len({c['nfs_slot'] for c in fleet}),7)
        for c in fleet:
            folder=ROOT/'modding/uma-steam/fleet'/str(c['id']);raw=json.loads((folder/'raw-model.json').read_text());gltf=json.loads((folder/'source.gltf').read_text());blob=(folder/'source.bin').read_bytes()
            self.assertEqual(len(blob),gltf['buffers'][0]['byteLength']);self.assertGreater(len(gltf['skins']),2)
            for view in gltf['bufferViews']:
                self.assertEqual(view['byteOffset']%4,0);self.assertLessEqual(view['byteOffset']+view['byteLength'],len(blob))
            for skin in gltf['skins']:
                self.assertTrue(all(0<=j<len(gltf['nodes']) for j in skin['joints']))
                self.assertEqual(gltf['accessors'][skin['inverseBindMatrices']]['count'],len(skin['joints']))
            eye=next(m for m in gltf['materials'] if m['name'].endswith('_eye'))
            self.assertEqual(eye['pbrMetallicRoughness']['baseColorTexture']['extensions']['KHR_texture_transform']['scale'],[.25,1.])
            for mesh in raw['meshes']:
                with np.load(folder/mesh['archive'],allow_pickle=False) as data:
                    self.assertLess(int(data['triangles'].max()),len(data['positions']));self.assertTrue(np.isfinite(data['positions']).all())
                    if mesh['skinned']:
                        self.assertEqual(data['weights'].shape,(mesh['vertices'],4));np.testing.assert_allclose(data['weights'].sum(1),1,atol=.01)
                        self.assertLess(int(data['bones'][data['weights']>0].max()),len(data['bind_poses']));np.testing.assert_allclose(data['bind_poses'][:,3,:],np.tile([0,0,0,1],(len(data['bind_poses']),1)),atol=1e-5)
            for texture in raw['textures']:self.assertTrue((folder/texture['png']).is_file())

    def test_original_clips_loop_and_animate_core_joints(self):
        for folder in (ROOT/'modding/uma-steam/fleet').iterdir():
            if not folder.is_dir() or not (folder/'source.gltf').exists():continue
            g=json.loads((folder/'source.gltf').read_text());blob=(folder/'source.bin').read_bytes()
            def array(index):
                a=g['accessors'][index];view=g['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
                return np.frombuffer(blob,dtype='<f4',count=a['count']*width,offset=view.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width)
            self.assertEqual({a['name'] for a in g['animations']},{'idle','run'})
            for animation in g['animations']:
                moving=set()
                for channel in animation['channels']:
                    sampler=animation['samplers'][channel['sampler']];times=array(sampler['input'])[:,0];values=array(sampler['output']);kind=channel['target']['path']
                    self.assertTrue(np.all(np.diff(times)>0));self.assertTrue(np.isfinite(values).all());self.assertEqual(len(times),len(values))
                    if kind=='rotation':
                        np.testing.assert_allclose(np.linalg.norm(values,axis=1),1,atol=1e-5);self.assertGreater(abs(float(values[0]@values[-1])),.9999)
                    else:np.testing.assert_allclose(values[0],values[-1],atol=1e-5)
                    if not np.allclose(values,values[0],atol=1e-4):moving.add(g['nodes'][channel['target']['node']]['name'])
                if animation['name']=='run':self.assertTrue({'Knee_L','Knee_R','Arm_L','Arm_R'}<=moving)
