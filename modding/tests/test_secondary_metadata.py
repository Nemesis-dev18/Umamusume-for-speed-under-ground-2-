import json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class SecondaryMetadata(unittest.TestCase):
 def test_parser_rejects_invalid_sidecars(self):
  exe=ROOT/'modding/runtime/test-build/secondary-test'
  subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(ROOT/'modding/runtime/secondary_test.c'),'-lm','-o',str(exe)],check=True)
  folder=ROOT/'modding/staged-runtime/fleet-secondary/1068';data=(folder/'secondary.bin').read_bytes();nb,nn,nc,nr=struct.unpack_from('<4I',data,8)
  invalid=[data[:n] for n in (0,4,23,24,71,len(data)-1)]+[data+b'\0']
  for offset,value in [(0,b'FAIL'),(4,struct.pack('<I',2)),(8,struct.pack('<I',nb+1)),(12,struct.pack('<I',513)),(24,struct.pack('<H',nb)),(26,struct.pack('<H',17)),(28,struct.pack('<H',65535)),(32,struct.pack('<f',float('nan'))),(24+48*nn+8,struct.pack('<f',float('inf'))),(24+48*nn+36*nc,struct.pack('<H',nc))]:
   changed=bytearray(data);changed[offset:offset+len(value)]=value;invalid.append(changed)
  with tempfile.TemporaryDirectory(dir=ROOT/'modding/runtime/test-build') as tmp:
   path=Path(tmp)/'secondary.bin'
   for i,binary in enumerate(invalid):
    path.write_bytes(binary)
    with self.subTest(case=i):self.assertEqual(subprocess.run([str(exe),str(folder/'model-atlas.umab'),str(path),'validate']).returncode,2)
   path.write_bytes(data);self.assertEqual(subprocess.run([str(exe),str(folder/'model-atlas.umab'),str(path),'validate']).returncode,0)
if __name__=='__main__':unittest.main()
