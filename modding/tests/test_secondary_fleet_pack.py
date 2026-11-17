import hashlib,json,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/scripts'))
from pack_steam_fleet import NativeSkin,AXES


class SecondaryFleetPack(unittest.TestCase):
    def test_c_player_matches_original_native_skinning(self):
        with tempfile.TemporaryDirectory(prefix='fleet-',dir=ROOT/'modding/runtime/test-build') as tmp:
            tmp=Path(tmp);exe=tmp/'skin-test'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(ROOT/'modding/runtime/fleet_motion_test.c'),'-lm','-o',str(exe)],check=True,capture_output=True)
            results=[]
            fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']
            for character in fleet:
                folder=ROOT/'modding/uma-steam/fleet'/str(character['id']);source=NativeSkin(folder,secondary=True);primitives=list(source.primitives());staged=ROOT/'modding/staged-runtime/fleet-secondary'/str(character['id']);report=json.loads((staged/'model.json').read_text());asset=staged/'model.umab'
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(),report['sha256']);self.assertEqual(hashlib.sha256((folder/'source.gltf').read_bytes()).hexdigest(),report['source_sha256'])
                self.assertEqual(hashlib.sha256((folder/'source.bin').read_bytes()).hexdigest(),report['source_buffer_sha256'])
                self.assertEqual(len({g['material'] for g in report['groups']}),len(report['groups']));self.assertEqual(sum(g['index_count'] for g in report['groups']),report['indices'])
                self.assertEqual(sum(g['eye_depth_off'] for g in report['groups']),1)
                reference=bytearray(struct.pack('<II',report['vertices'],8))
                for label in ('idle','run'):
                    frames=next(c['frames'] for c in report['clips'] if c['name']==label)
                    for frame in (0,frames//4,frames//2,frames-1):
                        world=source.pose(label,frame);parts=[source.deform(p,world) for p in primitives];positions=np.concatenate([p for p,n in parts])@AXES.T;normals=np.concatenate([n for p,n in parts])@AXES.T
                        self.assertTrue(np.isfinite(positions).all());self.assertTrue(np.isfinite(normals).all())
                        lowest=positions[:,2].min()
                        if lowest<-.0001:positions[:,2]+=-.0001-lowest
                        reference.extend(struct.pack('<3f',frame/frames if label=='idle' else 0,frame/frames if label=='run' else 0,float(label=='run')));reference.extend(np.concatenate([positions,normals],axis=1).astype('<f4').tobytes())
                path=tmp/'reference.bin';path.write_bytes(reference)
                with self.subTest(character=character['name']):
                    result=subprocess.run([str(exe),str(asset),str(path)],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr);results.append({'id':character['id'],'output':result.stdout.strip()})
            (ROOT/'modding/runtime/secondary-skin-verification.json').write_text(json.dumps({'cases_per_character':8,'comparison':'C UMAB skinning vs original native glTF joint matrices and inverse bind poses','results':results,'gameplay_verified':False},indent=2)+'\n')

if __name__=='__main__':unittest.main()
