import hashlib,json,struct,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/scripts'))
from fleet_carrier import carrier
from prepare_steam_fleet_geometry import solid_map
from extract_assets import payload,skip_words
from inspect_assets import chunks,flatten


class FleetGeometry(unittest.TestCase):
    def test_all_slots_have_only_carriers_and_correct_hulls(self):
        characters=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']
        for character in characters:
            with self.subTest(slot=character['nfs_slot']):
                folder=ROOT/'modding/staged-runtime/fleet'/str(character['id']);receipt=json.loads((folder/'geometry.json').read_text());data=(folder/'GEOMETRY.BIN').read_bytes();source=(ROOT/(receipt['target']+'.before-fleet-integration.bak')).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),receipt['after_sha256']);self.assertEqual(hashlib.sha256(source).hexdigest(),receipt['before_sha256']);self.assertFalse(receipt['installed'])
                self.assertEqual(solid_map(source).keys(),solid_map(data).keys());bodies=0
                for node,leaves,header in solid_map(data).values():
                    vb=payload(data,leaves['0x00134b01']);mh=payload(data,leaves['0x00134900']);mh=mh[skip_words(mh):];nv=struct.unpack_from('<I',mh,52)[0];nt=struct.unpack_from('<I',mh,36)[0]
                    if nv==6:
                        bodies+=1;self.assertEqual(nt,2);self.assertEqual(vb[-216:],carrier(character['id']));np.testing.assert_array_equal(np.array(struct.unpack_from('<16f',header,64)).reshape(4,4),np.eye(4))
                    else:
                        self.assertEqual((nv,nt),(3,1))
                        for v in range(3):self.assertEqual(struct.unpack_from('<3f',vb,len(vb)-108+v*36),(0,0,0))
                self.assertEqual(bodies,20)
                hulls=[n for n in flatten(chunks(data)) if n['id']=='0x00039201'];self.assertEqual(len(hulls),1 if character['nfs_slot'] in ('PEUGOT106','CORSA') else 5)
                for node,expected in zip(hulls,receipt['collision_hulls']):
                    points=np.array([struct.unpack_from('<3f',data,node['payload']+v*48+16) for v in range(node['size']//48)])
                    np.testing.assert_allclose(points.min(0),expected['new_minimum'],atol=1e-6);np.testing.assert_allclose(points.max(0),expected['new_maximum'],atol=1e-6)

if __name__=='__main__':unittest.main()
