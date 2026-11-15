import json
import struct
import subprocess
import sys
import unittest
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from inspect_assets import ROOT
from read_cri_audio import utf,awb
from extract_uma_footsteps import cue_waves

class CriAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank=(ROOT/'modding/uma-steam/audio/snd_sfx_race_000.acb').read_bytes();cls.header=utf(cls.bank)[1][0]

    def test_real_race_cues_resolve_to_valid_original_variants(self):
        _,entries=awb(self.header['AwbFile']);ids={ident for ident,_ in entries}
        self.assertEqual(len(entries),162);self.assertEqual(len(ids),162)
        for side in ['R','L']:
            variants=cue_waves(self.header,'snd_sfx_race_foot_turf_'+side);self.assertEqual(len(variants),10)
            for row in variants:self.assertIn(row['awb_id'],ids)
        with self.assertRaises(ValueError):cue_waves(self.header,'not-an-existing-cue')
        manifest=json.loads((ROOT/'modding/uma-steam/audio/race-footsteps/manifest.json').read_text())
        self.assertEqual(len(manifest['samples']),20)
        for row in manifest['samples']:
            self.assertGreater(row['key_validation_blocks'],0)
            with wave.open(str(ROOT/row['file']),'rb') as f:
                self.assertEqual((f.getnchannels(),f.getsampwidth(),f.getframerate()),(1,2,22050))
                self.assertAlmostEqual(f.getnframes()/22050,row['seconds'],places=6)

    def test_malformed_tables_and_archives_fail_closed(self):
        for data in [b'',b'@UTF'+b'\0'*28,self.bank[:-1]]:
            with self.assertRaises(ValueError):utf(data)
        source=self.header['AwbFile']
        for mode in ['width','count','offset','duplicate']:
            data=bytearray(source)
            if mode=='width':data[5]=3
            elif mode=='count':struct.pack_into('<I',data,8,100000)
            elif mode=='offset':struct.pack_into('<I',data,16+162*2,0xffffffff)
            else:data[18:20]=data[16:18]
            with self.assertRaises(ValueError):awb(data)

    def test_incorrect_hca_key_is_rejected_before_pcm_export(self):
        folder=ROOT/'modding/uma-steam/audio/race-footsteps';manifest=json.loads((folder/'manifest.json').read_text());ident=manifest['samples'][0]['awb_id'];output=folder/'wrong-key-test.pcm';output.unlink(missing_ok=True)
        process=subprocess.run([str(ROOT/'modding/uma-steam/audio-tools/clhca/decode-local'),str(folder/f'wave-{ident}.hca'),'0',str(output)],capture_output=True)
        self.assertEqual(process.returncode,5);self.assertFalse(output.exists())
