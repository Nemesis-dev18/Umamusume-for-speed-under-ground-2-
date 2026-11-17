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
