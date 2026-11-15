import io
import json
from pathlib import Path
import sys
import struct
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT,jdlz,chunks
from extract_assets import dds_header
from prepare_tiremask import rewrite_jdlz,prepare


class TireMask(unittest.TestCase):
    def test_literal_flags_boundaries(self):
        for size in [1,7,8,9,15,16,17,255,4096]:
            data=bytes(i%256 for i in range(size))
            stream=bytearray()
            for at in range(0,size,8):
                stream.append(0)
                if not at:stream.append(0)
                stream.extend(data[at:at+8])
            source=b'JDLZ\x02\x10\0\0'+struct.pack('<2I',size,len(stream)+16)+stream
            self.assertEqual(jdlz(rewrite_jdlz(source,data)),data)
        with self.assertRaises(ValueError):rewrite_jdlz(source,b'')

    def test_modified_reference_history_does_not_change_unrelated_output(self):
        for size,stream in [(21,bytes([2,1,97,0,17])),(34,bytes([0,0])+bytes(range(8))+bytes([0])+bytes(range(8,16))+bytes([2,16,14,0]))]:
            source=b'JDLZ\x02\x10\0\0'+struct.pack('<2I',size,len(stream)+16)+stream
            original=jdlz(source);desired=bytearray(original);desired[0]=55
            encoded=rewrite_jdlz(source,desired)
            self.assertEqual(jdlz(encoded),desired)
            self.assertEqual(jdlz(encoded)[1:],original[1:])

    def test_real_mask_all_mips_transparent_and_other_bytes_exact(self):
        plan=json.loads((ROOT/'modding/tiremask-plan.json').read_text());backup=ROOT/plan['backup']
        source=(backup if backup.exists() else ROOT/plan['target']).read_bytes()
        output,ranges=prepare(source);self.assertEqual(output,(ROOT/plan['candidate']).read_bytes())
        before,after=jdlz(source),jdlz(output);row=ranges[0];start=row['pixel_offset'];end=start+row['pixel_bytes']
        self.assertEqual(before[:start],after[:start]);self.assertEqual(before[end:],after[end:])
        self.assertEqual(chunks(before),chunks(after));at=start
        for level in range(5):
            width=max(1,128>>level);size=((width+3)//4)**2*8
            image=Image.open(io.BytesIO(dds_header(width,width,b'DXT1',size)+after[at:at+size])).convert('RGBA')
            self.assertEqual(image.getextrema()[3],(0,0));at+=size
        self.assertEqual(at,end)
        with self.assertRaises(ValueError):prepare(b'not a container')
