import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT
from prepare_character_name import entries,prepare
from disable_car_effects import string_hash


class CharacterName(unittest.TestCase):
    def source(self,language):
        path=ROOT/'LANGUAGES'/(language+'.bin');backup=path.with_name(path.name+'.before-kitasan-name.bak')
        return (backup if backup.exists() else path).read_bytes()

    def test_both_languages_preserve_all_other_strings_and_table_bytes(self):
        key=string_hash('CAR_NAME_COROLLA')
        for language in ['English','Spanish']:
            source=self.source(language);node,_,before=entries(source);output=prepare(source);new,_,after=entries(output)
            self.assertEqual({k:v for k,v,_ in after},{k:(b'Kitasan Black' if k==key else v) for k,v,_ in before})
            self.assertEqual(source[node['end']:],output[new['end']:])
            field=next(at+4 for k,_,at in before if k==key)
            for start,end in [(0,4),(8,field),(field+4,node['end'])]:self.assertEqual(source[start:end],output[start:end])
            self.assertEqual(new['size']%16,0)
            with self.assertRaises(ValueError):prepare(output)

    def test_corrupt_bounds_offsets_and_duplicates_fail(self):
        source=self.source('English');node,_,rows=entries(source)
        for cut in [0,7,15,100,len(source)-1]:
            with self.assertRaises(ValueError):entries(source[:cut])
        for offset,value in [(node['payload']+4,100001),(rows[0][2]+4,0xffffffff),(rows[1][2],rows[0][0])]:
            corrupt=bytearray(source);struct.pack_into('<I',corrupt,offset,value)
            with self.assertRaises(ValueError):entries(corrupt)
