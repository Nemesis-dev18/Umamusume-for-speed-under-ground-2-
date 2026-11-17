import io
import json
from pathlib import Path
import sys
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT,jdlz,chunks
from extract_assets import dds_header
from prepare_selection_label import dxt3


class SelectionLabel(unittest.TestCase):
    def test_alpha_nibbles_and_block_order(self):
        image=Image.new('RGBA',(8,8),(255,255,255,0))
        for y in range(8):
            for x in range(8):image.putpixel((x,y),(255,255,255,((x%4)+(y%4)*4)*17))
        encoded=dxt3(image);self.assertEqual(len(encoded),64)
        decoded=Image.open(io.BytesIO(dds_header(8,8,b'DXT3',64)+encoded)).convert('RGBA')
        self.assertEqual(decoded.getchannel('A').tobytes(),image.getchannel('A').tobytes())

    def test_only_reviewed_label_pixels_change_in_decoded_package(self):
        plan=json.loads((ROOT/'modding/selection-label-plan.json').read_text());backup=ROOT/plan['backup']
        source=jdlz((backup if backup.exists() else ROOT/plan['target']).read_bytes());candidate=jdlz((ROOT/plan['candidate']).read_bytes())
        start,end=plan['decoded_changed_range']
        self.assertEqual(source[:start],candidate[:start]);self.assertEqual(source[end:],candidate[end:]);self.assertNotEqual(source[start:end],candidate[start:end])
        self.assertEqual(chunks(source),chunks(candidate));self.assertEqual(len(source),plan['decoded_bytes'])
        image=Image.open(io.BytesIO(dds_header(256,64,b'DXT3',16384)+candidate[start:end])).convert('RGBA')
        self.assertEqual(image.getextrema()[3],(0,255));self.assertEqual(image.getpixel((0,0))[3],0)
