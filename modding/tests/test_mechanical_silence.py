import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_assets import ROOT
from prepare_mechanical_silence import mute_abk, mute_gin
from read_ea_sound import abk_samples


class MechanicalSilence(unittest.TestCase):
    def test_real_banks_preserve_programs_metadata_and_lengths(self):
        plan = json.loads((ROOT / 'modding/mechanical-silence-plan.json').read_text())
        self.assertEqual(len(plan['files']), 246)
        for item in plan['files']:
            with self.subTest(path=item['target']):
                backup = ROOT / item['backup']
                source = (backup if backup.exists() else ROOT / item['target']).read_bytes()
                output, ranges = (mute_gin if item['target'].endswith('.gin') else mute_abk)(source)
                self.assertEqual(hashlib.sha256(source).hexdigest(), item['before_sha256'])
                self.assertEqual(hashlib.sha256(output).hexdigest(), item['after_sha256'])
                self.assertEqual(output, (ROOT / item['candidate']).read_bytes())
                self.assertEqual(ranges, item['sample_ranges'])
                self.assertEqual(len(output), len(source))
                mask = np.zeros(len(source), dtype=bool)
                for row in ranges:
                    at, end = row['offset'], row['offset'] + row['bytes']
                    mask[at:end] = True
                    if item['target'].endswith('.gin'):
                        self.assertEqual(output[at:end], bytes(end-at))
                    else:
                        # Each decoded frame has zero history and zero residuals.
                        for _ in range((row['samples']+27)//28):
                            raw = source[at] == 238
                            size = 61 if raw else 15
                            self.assertEqual(output[at:at+size], b'\xee'+bytes(60) if raw else bytes(15))
                            at += size
                        self.assertEqual(at, end)
                a, b = np.frombuffer(source, dtype='u1'), np.frombuffer(output, dtype='u1')
                self.assertTrue(np.array_equal(a[~mask], b[~mask]))
                if item['target'].endswith('.abk'):
                    self.assertEqual(abk_samples(source), abk_samples(output))

    def test_invalid_container_bounds_rejected(self):
        with self.assertRaises(ValueError):
            mute_gin(b'Gnsu'+bytes(28))
        with self.assertRaises(ValueError):
            mute_abk(b'ABKC'+bytes(60))
        plan = json.loads((ROOT / 'modding/mechanical-silence-plan.json').read_text())
        item = next(x for x in plan['files'] if x['target'].endswith('.abk'))
        source = bytearray((ROOT / item['candidate']).read_bytes())
        base = struct.unpack_from('<I', source, 32)[0]
        struct.pack_into('<i', source, base+20, -20)
        with self.assertRaises(ValueError):
            abk_samples(source)
