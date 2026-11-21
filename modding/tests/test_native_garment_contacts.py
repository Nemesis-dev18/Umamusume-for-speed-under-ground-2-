import copy,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_native_garment_contacts import prepare

class NativeGarmentContacts(unittest.TestCase):
 def fixture(self):
  nodes=[(0,256,0,2,*([.1]*10)),(1,512,2,2,*([.2]*10))]
  raw=struct.pack('<4s5I',b'UMAS',1,2,2,3,4)+b''.join(struct.pack('<4H10f',*n) for n in nodes)+bytes(3*36)+struct.pack('<4H',2,0,2,1)
  meta={'spring_nodes':[{'bone':0,'name':'Sleeve','native':{'_collisionNameList':['NativeA']},'colliders':['NativeA','RuntimeTorso']},{'bone':1,'name':'Skirt','native':{'_collisionNameList':[]},'colliders':['RuntimeThigh','RuntimeTorso']}]}
  return raw,meta
 def test_metadata_order_and_empty_native_contacts(self):
  raw,meta=self.fixture();out,changes=prepare(raw,meta);self.assertEqual(len(changes),2)
  self.assertEqual(struct.unpack_from('<I',out,20)[0],1)
  self.assertEqual(struct.unpack_from('<2H',out,28),(0,1))
  self.assertEqual(struct.unpack_from('<2H',out,76),(1,0))
  self.assertEqual(struct.unpack_from('<H',out,24+96+108)[0],0)
  for at in (24,72):self.assertEqual(out[at+8:at+48],raw[at+8:at+48])
 def test_unsupported_source_plane_keeps_existing_fallback(self):
  raw,meta=self.fixture();meta=copy.deepcopy(meta);meta['spring_nodes'][0]['native']['_collisionNameList'].append('UnsupportedPlane')
  out,changes=prepare(raw,meta);self.assertEqual(struct.unpack_from('<I',out,20)[0],2)
  self.assertEqual(struct.unpack_from('<2H',out,24+96+108),(0,2))
  self.assertEqual(changes[0]['name'],'Skirt')
 def test_duplicate_reference_rejected(self):
  raw,meta=self.fixture();bad=bytearray(raw);struct.pack_into('<2H',bad,24+96+108,0,0)
  with self.assertRaises(AssertionError):prepare(bytes(bad),meta)

if __name__=='__main__':unittest.main()
