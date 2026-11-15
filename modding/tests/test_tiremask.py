import io
import json
from pathlib import Path
import sys
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT,jdlz,chunks
from extract_assets import dds_header
from prepare_tiremask import literal_jdlz,prepare


class TireMask(unittest.TestCase):
    def test_literal_flags_boundaries(self):
        for size in [1,7,8,9,15,16,17,255,4096]:
            data=bytes(i%256 for i in range(size))
            self.assertEqual(jdlz(literal_jdlz(data)),data)
        with self.assertRaises(ValueError):literal_jdlz(b'')

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
