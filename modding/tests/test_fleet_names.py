import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/scripts'))
from prepare_character_name import prepare_names,entries
from disable_car_effects import string_hash

class FleetNames(unittest.TestCase):
    def test_seven_names_preserve_every_other_language_entry(self):
        names={c['nfs_slot']:c['name'] for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']}
        for language in ('English','Spanish'):
            before=(ROOT/'LANGUAGES'/(language+'.bin')).read_bytes();after=prepare_names(before,names);old={k:v for k,v,_ in entries(before)[2]};new={k:v for k,v,_ in entries(after)[2]};expected={string_hash('CAR_NAME_'+s):v.encode() for s,v in names.items()}
            self.assertEqual(new,{k:expected.get(k,v) for k,v in old.items()})
            with self.assertRaises(ValueError):prepare_names(before,{'NOT_A_SLOT':'Nobody'})
            with self.assertRaises(ValueError):prepare_names(before,{'COROLLA':'bad\0label'})
