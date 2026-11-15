import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT
from retarget_uma_motion import UmaRetarget

class OriginalMotionRetarget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.motion=UmaRetarget()

    def test_source_loop_and_mapping(self):
        clip=self.motion.clip
        self.assertAlmostEqual(clip.duration,.6,places=5)
        self.assertEqual(len(clip.bindings),109)
        self.assertEqual(len(clip.unmapped),14)
        start,end=clip.channels(0),clip.channels(1)
        for key in start:self.assertTrue(np.array_equal(start[key],end[key]))

    def test_limb_direction_fidelity_and_bone_lengths(self):
        actor=self.motion;target=actor.target
        for phase in (0,.125,.25,.375,.5,.75):
            _,source=actor.source.pose(actor.clip.channels(phase));rotation,offset,positions,_=actor.pose(phase)
            self.assertTrue(np.allclose(np.linalg.det(rotation),1,atol=1e-6))
            for a,b,sa,sb in actor.limbs:
                actual=positions[b]-positions[a];expected=actor.axes@(source[sb]-source[sa]);actual/=np.linalg.norm(actual);expected/=np.linalg.norm(expected)
                self.assertGreater(float(actual@expected),.99999)
            for i,bone in enumerate(target.bones):
                parent=bone['parent']
                if parent>=0 and i!=target.named['センター']:
                    self.assertAlmostEqual(float(np.linalg.norm(positions[i]-positions[parent])),float(np.linalg.norm(target.rest[i]-target.rest[parent])),places=5)
            mesh,normals=target.skin(rotation,offset)
            self.assertGreaterEqual(float(mesh[:,2].min()),-.000101)
            self.assertTrue(np.isfinite(normals).all())

    def test_model_and_binding_prefix_unchanged(self):
        import struct
        candidate=(ROOT/'modding/staged-runtime/kitasan-steam.umab').read_bytes()
        baseline_path=ROOT/'modding/runtime/kitasan.before-steam.umab'
        baseline=(baseline_path if baseline_path.exists() else ROOT/'modding/runtime/kitasan.umab').read_bytes()
        _,version,nv,ni,nb,_,_,_=struct.unpack_from('<4s7I',candidate)
        self.assertEqual(version,2)
        prefix=32+nv*60+nb*16+((ni*2+3)//4)*4
        self.assertEqual(candidate[:prefix],baseline[:prefix])
        self.assertNotEqual(candidate[prefix:],baseline[prefix:])

class SteamMotionBounds(unittest.TestCase):
    def test_only_expanding_bounds_fields(self):
        from prepare_steam_bounds import prepare
        import json
        plan=json.loads((ROOT/'modding/steam-motion-bounds-plan.json').read_text())
        path=ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-steam-motion.bak'
        source=(path if path.exists() else ROOT/'CARS/COROLLA/GEOMETRY.BIN').read_bytes()
        candidate,changes=prepare(source,plan['minimum'],plan['maximum'])
        self.assertEqual(candidate,(ROOT/'modding/staged-runtime/GEOMETRY-steam-motion.BIN').read_bytes())
        self.assertEqual(changes,plan['fields'])
        allowed={i for f in changes for i in range(f['offset'],f['offset']+4)}
        self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(source,candidate))))
