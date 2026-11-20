import math,struct,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]

class GentildonnaScale(unittest.TestCase):
 def test_height_relative_to_kitasan_preserves_detail(self):
  def mesh(path):
   data=path.read_bytes();nv,ni,nb=struct.unpack_from('<3I',data,8);return (nv,ni,nb),np.ndarray((nv,8),'<f4',data,40,strides=(36,4))
  counts,vertices=mesh(ROOT/'modding/staged-runtime/gentildonna/model.umab');_,kita=mesh(ROOT/'modding/runtime/fleet/1068/model.umab')
  self.assertEqual(counts,(29023,134016,271));self.assertAlmostEqual(float(np.ptp(vertices[:,2])),1.78,places=5)
  self.assertGreater(float(np.ptp(vertices[:,2])),float(np.ptp(kita[:,2])))
  self.assertLess(float(np.ptp(vertices[:,2])),float(np.ptp(kita[:,2]))*1.1)
 def test_all_secondary_chains_are_damped(self):
  data=(ROOT/'modding/staged-runtime/gentildonna/secondary.bin').read_bytes();count=struct.unpack_from('<I',data,12)[0];self.assertEqual(count,123)
  for i in range(count):
   node=struct.unpack_from('<4H10f',data,24+i*48);self.assertEqual(node[1],256);self.assertGreaterEqual(node[8],1.1)
   self.assertLess(node[11]*node[13],.1)

if __name__=='__main__':unittest.main()
