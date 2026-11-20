"""Exercise real file replacement and rollback inside a disposable local fixture."""
import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT/'modding/scripts'))
import install_gentildonna_package as installer

class Installation(unittest.TestCase):
 def exercise(self,fail=False,stale=False):
  with tempfile.TemporaryDirectory(dir=ROOT/'modding/runtime',prefix='install-fixture-') as name:
   root=Path(name);rows=[]
   for i in range(3):
    candidate=root/f'candidate-{i}';candidate.write_bytes(b'new'+bytes([i]));target=root/f'target-{i}';backup=root/f'backup-{i}'
    if i<2:target.write_bytes(b'old'+bytes([i]));backup.write_bytes(target.read_bytes())
    rows.append({'target':target.name,'candidate':candidate.name,'before':installer.digest(target) if i<2 else None,'after':installer.digest(candidate),'backup':backup.name if i<2 else None})
   plan=root/'plan.json';plan.write_text(json.dumps({'installed':False,'files':rows}));replace=installer.os.replace
   def operation(src,dst):
    if fail and Path(dst).name=='target-1':raise OSError('injected replacement failure')
    return replace(src,dst)
   temporary=root/'target-0.gentildonna.tmp'
   if stale:temporary.write_bytes(b'preexisting user file')
   with patch.object(installer,'ROOT',root),patch.object(installer,'PLAN',plan),patch.object(installer,'game_closed'),patch.object(installer.subprocess,'check_output',return_value='fixture\n'),patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0)),patch.object(installer.os,'replace',side_effect=operation):
    if fail or stale:
     with self.assertRaises(OSError):installer.install()
    else:installer.install()
   for i in range(3):
    target=root/f'target-{i}'
    if fail or stale:
     if i<2:self.assertEqual(target.read_bytes(),b'old'+bytes([i]))
     else:self.assertFalse(target.exists())
    else:self.assertEqual(target.read_bytes(),b'new'+bytes([i]))
   if stale:self.assertEqual(temporary.read_bytes(),b'preexisting user file')
   else:self.assertFalse(list(root.glob('*.gentildonna.tmp')))
   self.assertEqual(json.loads(plan.read_text())['installed'],not(fail or stale))
 def test_success(self):self.exercise()
 def test_rollback(self):self.exercise(fail=True)
 def test_does_not_remove_preexisting_temporary(self):self.exercise(stale=True)

if __name__=='__main__':unittest.main()
