import json
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT,chunks
from prepare_shared_parts import prepare
from extract_assets import geometry

class SharedParts(unittest.TestCase):
    def test_all_candidates_only_degenerate_triangle_indices(self):
        plan=json.loads((ROOT/'modding/shared-parts-plan.json').read_text())
        self.assertEqual(len(plan['files']),12)
        count=0
        for item in plan['files']:
            target=ROOT/item['target'];backup=target.with_name('GEOMETRY.BIN.before-uma-parts.bak')
            source=(backup if backup.exists() else target).read_bytes();candidate,ranges=prepare(source)
            self.assertEqual(candidate,(ROOT/item['candidate']).read_bytes());self.assertEqual(ranges,item['index_ranges'])
            mask=np.zeros(len(source),dtype=bool)
            for row in ranges:mask[row['offset']:row['offset']+row['bytes']]=True
            original=np.frombuffer(source,dtype='u1');modified=np.frombuffer(candidate,dtype='u1')
            self.assertTrue(np.array_equal(original[~mask],modified[~mask]));self.assertTrue(np.all(modified[mask]==0))
            self.assertEqual(chunks(candidate),chunks(source))
            meshes=geometry(candidate,'');count+=len(meshes)
            for mesh in meshes:self.assertTrue(all(index==0 for index in mesh['indices']))
        self.assertEqual(count,2192)
