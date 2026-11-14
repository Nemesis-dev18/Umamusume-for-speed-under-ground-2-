import json
import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_character_collision import prepare,LOWER,UPPER
from inspect_assets import ROOT,chunks,flatten

class CharacterCollision(unittest.TestCase):
    def test_only_collision_coordinates_change_and_topology_is_identical(self):
        backup=ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-character-collision.bak'
        source=(backup if backup.exists() else ROOT/'CARS/COROLLA/GEOMETRY.BIN').read_bytes()
        candidate,groups,ranges=prepare(source)
        self.assertEqual(len(candidate),len(source));self.assertEqual(chunks(candidate),chunks(source))
        self.assertEqual(candidate,(ROOT/'modding/staged-runtime/GEOMETRY-character-collision.BIN').read_bytes())
        self.assertEqual(len(groups),5);self.assertEqual(len(ranges),230)
        mask=np.zeros(len(source),dtype=bool)
        for item in ranges:mask[item['offset']:item['offset']+item['bytes']]=True
        before=np.frombuffer(source,dtype='u1');after=np.frombuffer(candidate,dtype='u1')
        self.assertTrue(np.array_equal(before[~mask],after[~mask]))
        for group in groups:
            self.assertTrue(all(x>0 for x in group['scale']))
            self.assertGreater(group['old_maximum'][0]-group['old_minimum'][0],3.8)
        for node in flatten(chunks(candidate)):
            if node['id']=='0x00039201':
                points=np.array([struct.unpack_from('<3f',candidate,node['payload']+v*48+16) for v in range(node['size']//48)])
                self.assertTrue(np.allclose(points.min(0),LOWER,atol=1e-6));self.assertTrue(np.allclose(points.max(0),UPPER,atol=1e-6))
                self.assertLess(float(points.max(0)[0]),.66)
                self.assertGreater(float(points.min(0)[0]),-.36)

    def test_unexpected_character_or_record_rejected(self):
        backup=ROOT/'CARS/COROLLA/GEOMETRY.BIN.before-character-collision.bak'
        source=bytearray((backup if backup.exists() else ROOT/'CARS/COROLLA/GEOMETRY.BIN').read_bytes())
        point=next(n for n in flatten(chunks(source)) if n['id']=='0x00039201')
        struct.pack_into('<I',source,point['payload'],99)
        with self.assertRaises(ValueError):prepare(source)
