import sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pack_steam_atlas import diffuse_images

class FaceAtlasOrder(unittest.TestCase):
 def test_shared_brow_texture_always_uses_baked_face(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
   folder=Path(tmp);(folder/'runtime').mkdir();Image.new('RGBA',(2,2),'white').save(folder/'original.png');Image.new('RGBA',(2,2),'green').save(folder/'runtime/face-baked.png')
   g={'textures':[{'source':0}],'images':[{'uri':'original.png'}]};groups=[{'texture':0,'material':'chr_mayu'},{'texture':0,'material':'chr_face'}]
   for order in (groups,list(reversed(groups))):
    self.assertEqual(diffuse_images(folder,g,order)[0].getpixel((0,0)),(0,128,0,255))
 def test_nonface_texture_unchanged(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
   folder=Path(tmp);Image.new('RGBA',(2,2),'red').save(folder/'original.png');g={'textures':[{'source':0}],'images':[{'uri':'original.png'}]}
   self.assertEqual(diffuse_images(folder,g,[{'texture':0,'material':'chr_hair'}])[0].getpixel((0,0)),(255,0,0,255))
if __name__=='__main__':unittest.main()
