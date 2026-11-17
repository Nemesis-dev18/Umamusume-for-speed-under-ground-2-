import struct
import unittest
from inspect_assets import ROOT,jdlz
from jdlz_native import finish_native,validate_native
from prepare_shadow_guard import descriptors
from disable_car_effects import string_hash

class NativeJdlz(unittest.TestCase):
    def stream(self,folder,slot,suffix):
        data=(ROOT/folder/slot/'TEXTURES.BIN').read_bytes();_,e=descriptors(data)[string_hash(slot+'_SHADOW'+suffix)]
        return data[e[1]:e[1]+e[2]]
    def test_terminal_literal_flag_refill(self):
        source=b'JDLZ\x02\x10\0\0'+struct.pack('<II',8,26)+bytes(2)+b'12345678'
        self.assertEqual(jdlz(source),b'12345678')
        with self.assertRaises(ValueError):validate_native(source)
        fixed=finish_native(source);self.assertEqual(len(fixed),27);self.assertEqual(validate_native(fixed),b'12345678')
        self.assertEqual(finish_native(fixed),fixed)
    def test_captured_shadow_failure_cases(self):
        for folder,slot,suffix in [('modding/staged-runtime/fleet-shadows','PEUGOT106','FE'),('modding/staged-runtime/fleet-shadows-short-copy','COROLLA','IG')]:
            with self.subTest(slot=slot,suffix=suffix):
                source=self.stream(folder,slot,suffix)
                with self.assertRaises(ValueError):validate_native(source)
                fixed=finish_native(source);self.assertEqual(len(fixed),len(source)+1)
                self.assertEqual(validate_native(fixed),jdlz(source))
    def test_all_original_and_finalized_streams(self):
        for slot in ['COROLLA','240SX','MIATA','FOCUS','PEUGOT','PEUGOT106','CORSA']:
            for suffix in ['FE','IG']:
                original=self.stream('CARS',slot,suffix);self.assertEqual(validate_native(original),jdlz(original))
                for folder in ['modding/staged-runtime/fleet-shadows','modding/staged-runtime/fleet-shadows-short-copy']:
                    source=self.stream(folder,slot,suffix);self.assertEqual(validate_native(finish_native(source)),jdlz(source))
