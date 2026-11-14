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

class Huffman(unittest.TestCase):
    def test_minimal_canonical_stream(self):
        from inspect_assets import huff
        # Two one-bit symbols (0 and 1), clue 255, one zero byte output.
        bits=f'{0x30fb:016b}'+f'{1:024b}'+f'{255:08b}'+'110'+'100'+'100'+'0'
        bits+='0'*(-len(bits)%8)
        body=int(bits,2).to_bytes(len(bits)//8,'big')
        stream=b'HUFF\x01\x10\0\0'+struct.pack('<II',1,len(body))+body
        self.assertEqual(huff(stream),b'\0')
        with self.assertRaises(ValueError):huff(stream[:-1])
    def test_real_headers(self):
        from inspect_assets import chunks,flatten,huff,ROOT
        data=(ROOT/'CARS/COROLLA/TEXTURES.BIN').read_bytes();count=0
        for node in flatten(chunks(data)):
            if node['id']!='0x33310003':continue
            for i in range(node['payload'],node['end'],24):
                key,off,size,out,back,_=struct.unpack_from('<6I',data,i)
                if data[off:off+4]!=b'HUFF':continue
                pool=huff(data[off:off+size])
                self.assertEqual(len(pool),out)
                self.assertEqual(struct.unpack_from('<I',pool,out-back+0x88)[0],key)
                count+=1
        self.assertEqual(count,13)


class Mips(unittest.TestCase):
    def test_exact_chain(self):
        from extract_assets import mip_layout
        levels=mip_layout(32,32,0x24,1344)
        self.assertEqual([(p['width'],p['bytes']) for p in levels],[(32,1024),(16,256),(8,64)])
        for size in (0,1343,1345,2000):
            with self.assertRaises(ValueError):mip_layout(32,32,0x24,size)
    def test_mip_dds(self):
        from extract_assets import dds_header
        header=dds_header(32,32,b'DXT3',1024,3)
        self.assertEqual(struct.unpack_from('<I',header,28)[0],3)
        self.assertTrue(struct.unpack_from('<I',header,8)[0]&0x20000)


class CarTypes(unittest.TestCase):
    def test_real_table_and_empty_rejection(self):
        from inspect_assets import ROOT,cartypes
        self.assertEqual(cartypes(b'CARS/COROLLA/GEOMETRY.BIN'),[])
        records=cartypes((ROOT/'GLOBAL/GLOBALB.BUN').read_bytes())
        self.assertEqual(len(records),46)
        self.assertEqual(len([r for r in records if r['name']=='COROLLA']),1)
        for record in records:self.assertEqual(len(record['wheels']),4)

if __name__ == '__main__': unittest.main()
