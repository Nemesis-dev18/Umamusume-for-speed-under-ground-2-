import math,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class CapeProfile(unittest.TestCase):
 def test_mambo_softness_keeps_bounded_linked_panels(self):
  data=(ROOT/'modding/staged-runtime/fleet-secondary/1062/secondary.bin').read_bytes();count=struct.unpack_from('<I',data,12)[0];cape=[]
  for i in range(count):
   node=struct.unpack_from('<4H10f',data,24+i*48)
   if node[1]&31:cape.append(node)
  self.assertEqual(len(cape),16)
  for node in cape:
   depth=(node[1]&31)-1
   self.assertAlmostEqual(node[7],(1.3,1.6,1.8,2.0)[depth],places=5)
   self.assertAlmostEqual(node[8],1.05,places=5)
   self.assertAlmostEqual(node[11],math.radians((55.,35.,30.,25.)[depth]),places=5)
   self.assertGreater(node[11],0)
if __name__=='__main__':unittest.main()
