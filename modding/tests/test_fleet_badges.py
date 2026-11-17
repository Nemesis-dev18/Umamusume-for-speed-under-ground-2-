import hashlib,json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/scripts'))
from inspect_assets import jdlz,cartypes
from prepare_fleet_badges import directory,NAMES
from disable_car_effects import string_hash


class FleetBadges(unittest.TestCase):
    def test_badges_and_global_mapping_preserve_unrelated_data(self):
        plan=json.loads((ROOT/'modding/fleet-badge-plan.json').read_text());source=(ROOT/(plan['target']+'.before-fleet-chibi.bak')).read_bytes();candidate=(ROOT/plan['candidate']).read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),plan['before_sha256']);self.assertEqual(hashlib.sha256(candidate).hexdigest(),plan['after_sha256'])
        before=jdlz(source);after=jdlz(candidate);a=directory(before);b=directory(after);self.assertEqual(len(b),len(a)+6);kitasan=string_hash('CARSELECT_MANUFACTURER_KITASAN')
        for key,(offset,size,header) in a.items():
            new_offset,new_size,new_header=b[key];self.assertEqual(header,new_header);self.assertEqual(size,new_size)
            if key!=kitasan:self.assertEqual(before[offset:offset+size],after[new_offset:new_offset+new_size])
        for name in NAMES.values():
            offset,size,header=b[string_hash('CARSELECT_MANUFACTURER_'+name)];self.assertEqual(offset%128,0);self.assertEqual(size,8192)
        mapping=json.loads((ROOT/'modding/fleet-badge-mapping-plan.json').read_text())
        for record in mapping['files']:
            old=(ROOT/(record['target']+'.before-fleet-chibi.bak')).read_bytes();new=(ROOT/record['candidate']).read_bytes();self.assertEqual(hashlib.sha256(old).hexdigest(),record['before_sha256']);self.assertEqual(hashlib.sha256(new).hexdigest(),record['after_sha256'])
            old=jdlz(old) if old.startswith(b'JDLZ') else old;new=jdlz(new) if new.startswith(b'JDLZ') else new;self.assertEqual(len(old),len(new));mask=np.zeros(len(old),bool)
            cars={c['name']:c for c in cartypes(new)}
            for field in record['fields']:
                at=field['offset'];self.assertEqual(at,cars[field['slot']]['offset']+0xc0);self.assertEqual(new[at:at+16],field['after'].encode().ljust(16,b'\0'));self.assertIn(int(field['texture_hash'],16),b);mask[at:at+16]=True
            self.assertFalse(np.any((np.frombuffer(old,'u1')!=np.frombuffer(new,'u1'))&~mask))

if __name__=='__main__':unittest.main()
