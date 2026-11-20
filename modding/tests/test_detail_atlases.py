import json,struct,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
class DetailAtlases(unittest.TestCase):
 def test_all_seven_preserve_native_diffuse_texels_and_installed_animation(self):
  plan=json.loads((ROOT/'modding/detail-atlas-plan.json').read_text());self.assertEqual(len(plan['characters']),7)
  for row in plan['characters']:
   with self.subTest(character=row['id']):
    folder=ROOT/'modding/uma-steam/fleet'/str(row['id']);out=ROOT/row['folder'];g=json.loads((folder/'source.gltf').read_text());report=json.loads((folder/'runtime/model.json').read_text());meta=json.loads((out/'detail.json').read_text())
    self.assertEqual(meta['size'],[4096,4096]);self.assertTrue(meta['installed_rig_preserved']);self.assertEqual(len(meta['levels']),13)
    baked_face_textures={group['texture'] for group in report['groups'] if group['material'].endswith('_face')}
    with Image.open(out/'atlas.png') as atlas:
     for group in report['groups']:
      tex=group['texture'];image_path=folder/g['images'][g['textures'][tex]['source']]['uri']
      if tex in baked_face_textures:image_path=folder/'runtime/face-baked.png'
      cell=meta['layout'][str(tex)]
      with Image.open(image_path) as original:
       self.assertEqual((cell['width'],cell['height']),original.size)
       crop=atlas.crop((cell['x'],cell['y'],cell['x']+cell['width'],cell['y']+cell['height']))
       self.assertEqual(crop.convert('RGB').tobytes(),original.convert('RGB').tobytes())
    before=(ROOT/'modding/runtime/fleet'/str(row['id'])/'model.umab').read_bytes();after=(out/'model.umab').read_bytes();nv=struct.unpack_from('<I',before,8)[0]
    self.assertEqual(before[:40],after[:40]);self.assertEqual(before[40+nv*36:],after[40+nv*36:])
    for i in range(nv):self.assertEqual(before[40+i*36:68+i*36],after[40+i*36:68+i*36])
    dds=(out/'atlas.dds').read_bytes();self.assertEqual(dds[84:88],b'DXT5');self.assertLess(len(dds),32*1024*1024)
if __name__=='__main__':unittest.main()
