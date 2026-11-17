import unittest
from inspect_assets import ROOT,jdlz
from prepare_miata_unlock import prepare

class MiataUnlock(unittest.TestCase):
    def test_only_miata_prerequisite_changes(self):
        for name in ['GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc']:
            with self.subTest(name=name):
                path=ROOT/name;backup=path.with_name(path.name+'.before-tachyon-unlock.bak')
                source=(backup if backup.exists() else path).read_bytes();candidate,field=prepare(source)
                old=jdlz(source) if source.startswith(b'JDLZ') else source
                new=jdlz(candidate) if candidate.startswith(b'JDLZ') else candidate
                at=field['decoded_offset'];self.assertEqual(len(old),len(new))
                self.assertEqual(old[:at],new[:at]);self.assertEqual(old[at+4:],new[at+4:]);self.assertEqual(new[at:at+4],bytes(4))
                with self.assertRaises(ValueError):prepare(candidate)
