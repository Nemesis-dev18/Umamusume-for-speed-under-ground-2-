import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT,chunks

class SelectableLights(unittest.TestCase):
    def test_candidates_only_change_light_indices_and_marker_hashes(self):
        plan=json.loads((ROOT/'modding/selectable-lights-plan.json').read_text())
        self.assertEqual(set(plan['missing_regional_resources']),{'CIVIC','RSX'})
        self.assertGreater(len(plan['files']),20)
        for row in plan['files']:
            path=ROOT/row['target'];backup=ROOT/row['backup'];source=(backup if backup.exists() else path).read_bytes();after=(ROOT/row['candidate']).read_bytes()
            self.assertEqual(hashlib.sha256(source).hexdigest(),row['before_sha256']);self.assertEqual(hashlib.sha256(after).hexdigest(),row['after_sha256'])
            self.assertEqual(len(source),len(after));self.assertEqual(chunks(source),chunks(after));expected=bytearray(source)
            for item in row['index_ranges']:
                start,size=item['offset'],item['bytes'];self.assertTrue(any(n in item['name'] for n in ('HEADLIGHT','BRAKELIGHT')))
                self.assertEqual(size%6,0);self.assertEqual(after[start:start+size],bytes(size));expected[start:start+size]=bytes(size)
            for item in row['markers']:
                start=item['offset'];self.assertEqual(source[start:start+4].hex(),item['before']);self.assertEqual(after[start:start+4].hex(),item['after']);expected[start:start+4]=bytes.fromhex(item['after'])
            self.assertEqual(bytes(expected),after,'Non-light bytes changed: '+row['target'])
