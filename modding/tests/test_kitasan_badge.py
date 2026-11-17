import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_kitasan_badge import badge,literal_jdlz
from inspect_assets import ROOT,chunks,flatten,jdlz

class BadgeTests(unittest.TestCase):
    def test_literal_roundtrip(self):
        for size in (1,8,9,16,257):
            data=bytes(i%256 for i in range(size))
            self.assertEqual(jdlz(literal_jdlz(data)),data)

    def test_existing_textures_preserved(self):
        raw=jdlz((ROOT/'FRONTEND/FrontB.lzc.before-kitasan-badge.bak').read_bytes())
        after,key=badge(raw,bytes(8192))
        def records(data):
            t=next(n for n in chunks(data) if n['offset']==204288)
            ns={n['id']:n for n in flatten(t['children'])}
            info=ns['0x33310004'];pool=ns['0x33320002'];out={}
            for at in range(info['payload'],info['end'],124):
                h=data[at:at+124];k=struct.unpack_from('<I',h,36)[0]
                offset=struct.unpack_from('<I',h,48)[0];size=struct.unpack_from('<I',h,56)[0]
                start=pool['payload']+120+offset
                self.assertEqual(start%128,0)
                out[k]=(h,data[start:start+size])
            return out
        before=records(raw);updated=records(after)
        self.assertEqual(set(updated)-set(before),{key})
        for k,value in before.items():self.assertEqual(updated[k],value)
        self.assertEqual(len(updated[key][1]),8192)
