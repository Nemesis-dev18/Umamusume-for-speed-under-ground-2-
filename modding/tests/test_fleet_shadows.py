"""Verify every character shadow, including slots other than Corolla."""
import json
import unittest
from inspect_assets import ROOT
from verify_foot_shadow import verify

class FleetShadowCandidates(unittest.TestCase):
    def test_all_seven_candidates(self):
        rows=json.loads((ROOT/'modding/fleet-shadow-plan.json').read_text())['files']
        self.assertEqual(len(rows),7)
        for row in rows:
            with self.subTest(slot=row['slot']):
                original=(ROOT/(row['target']+'.before-compact-shadows-motion.bak')).read_bytes()
                candidate=(ROOT/row['candidate']).read_bytes()
                result=verify(original,candidate,row['slot'])
                self.assertTrue(result['metadata_unchanged'])
                with self.assertRaises(ValueError):verify(original,candidate[:-1],row['slot'])
                wrong='240SX' if row['slot']=='COROLLA' else 'COROLLA'
                with self.assertRaises(ValueError):verify(original,candidate,wrong)

    def test_short_copy_rewrite_preserves_output_and_default_stream(self):
        from prepare_shadow_guard import descriptors
        from prepare_tiremask import rewrite_jdlz
        from disable_car_effects import string_hash
        from inspect_assets import jdlz
        raw=(ROOT/'modding/staged-runtime/fleet-shadows/COROLLA/TEXTURES.BIN').read_bytes()
        _,entry=descriptors(raw)[string_hash('COROLLA_SHADOWFE')]
        source=raw[entry[1]:entry[1]+entry[2]];decoded=jdlz(source)
        self.assertEqual(rewrite_jdlz(source,decoded),source)
        for limit in (3,4,511,512):
            with self.subTest(limit=limit):
                encoded=rewrite_jdlz(source,decoded,max_copy=limit)
                self.assertEqual(jdlz(encoded),decoded)
                self.assertGreater(len(encoded),len(source))
        for limit in (0,2,4099,float('nan')):
            with self.assertRaises(ValueError):rewrite_jdlz(source,decoded,max_copy=limit)
