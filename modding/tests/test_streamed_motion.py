import struct,sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from read_uma_motion import StreamedCurves

class StreamedMotion(unittest.TestCase):
    def stream(self,frames,count=1):
        raw=bytearray()
        for time,keys in frames:
            raw.extend(struct.pack('<fI',time,len(keys)))
            for index,coeff in keys:raw.extend(struct.pack('<I4f',index,*coeff))
        return {'curveCount':count,'data':np.frombuffer(raw,dtype='<u4').tolist()}

    def test_linear_cubic_and_stepped_keys(self):
        clip=self.stream([(-float('inf'),[(0,[0,0,0,4])]),(0,[(0,[0,0,2,1])]),(1,[(0,[1,2,3,4])]),(2,[(0,[0,0,0,10])])])
        stream=StreamedCurves(clip)
        self.assertAlmostEqual(stream.sample(.5)[0],2)
        self.assertAlmostEqual(stream.sample(1.5)[0],6.125)
        self.assertEqual(stream.sample(2.5)[0],10)

    def test_truncation_and_bad_index_rejected(self):
        bad=self.stream([(0,[(1,[0,0,0,1])])])
        with self.assertRaises(ValueError):StreamedCurves(bad)
        bad=self.stream([(0,[(0,[0,0,0,1])])]);bad['data'].pop()
        with self.assertRaises(ValueError):StreamedCurves(bad)
