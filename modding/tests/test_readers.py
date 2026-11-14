import sys
import struct
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_assets import chunks, data_path, jdlz

class Readers(unittest.TestCase):
    def test_literal_and_overlapping_copy(self):
        body = bytes([2, 1, 65, 0, 0])
        stream = b'JDLZ\x02\x10\0\0' + struct.pack('<II', 4, 16 + len(body)) + body
        self.assertEqual(jdlz(stream), b'AAAA')
    def test_corrupt_jdlz(self):
        for stream in (b'JDLZ', b'JDLZ\x02\x10\0\0' + struct.pack('<II', 2**30, 16),
                       b'JDLZ\x02\x10\0\0' + struct.pack('<II', 3, 20) + bytes([1,1,0,0])):
            with self.assertRaises(ValueError): jdlz(stream)
    def test_parent_boundary(self):
        child = struct.pack('<II', 1, 12)
        parent = struct.pack('<II', 0x80134000, len(child)) + child
        with self.assertRaises(ValueError): chunks(parent)
    def test_nested_offsets(self):
        data = struct.pack('<IIII', 0x80134000, 8, 0x134011, 0)
        tree = chunks(data)
        self.assertEqual(tree[0]['children'][0]['offset'], 8)
    def test_scope(self):
        for name in ('../SPEED2.EXE','SPEED2.EXE','CARS/../SPEED2.EXE','CARS/test.dll'):
            with self.assertRaises(ValueError): data_path(name)

if __name__ == '__main__': unittest.main()

class Geometry(unittest.TestCase):
    def test_real_corolla_and_source_stability(self):
        import hashlib
        from inspect_assets import ROOT
        from extract_assets import geometry
        path=ROOT/'CARS/COROLLA/GEOMETRY.BIN'
        before=hashlib.sha256(path.read_bytes()).digest()
        parts=geometry(path.read_bytes(),'KIT00_BODY_')
        self.assertEqual(len(parts),4)
        for part in parts:
            self.assertEqual(len(part['positions']),14512)
            self.assertEqual(len(part['indices']),16557*3)
            self.assertLess(max(part['indices']),len(part['positions']))
            self.assertIsNone(part['native_bones'])
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).digest())
    def test_globalb_golden_pair(self):
        from inspect_assets import ROOT
        self.assertEqual(jdlz((ROOT/'GLOBAL/GlobalB.lzc').read_bytes()),(ROOT/'GLOBAL/GLOBALB.BUN').read_bytes())
    def test_dds_header(self):
        from extract_assets import dds_header
        header=dds_header(8,8,b'DXT1',32)
        self.assertEqual(len(header),128)
        self.assertEqual(header[84:88],b'DXT1')
