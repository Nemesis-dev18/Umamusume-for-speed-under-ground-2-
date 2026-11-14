import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from make_hoof_audio import impact,pcm,RATE

class HoofAudio(unittest.TestCase):
    def test_original_impacts_are_repeatable_distinct_and_faded(self):
        first=impact(10);second=impact(23)
        self.assertTrue(np.array_equal(first,impact(10)))
        self.assertFalse(np.array_equal(first,second))
        self.assertEqual(first[0],0);self.assertEqual(first[-1],0)
        self.assertGreater(float(np.sqrt(np.mean(first[:int(RATE*.04)]**2))),.05)
        self.assertLess(float(np.max(np.abs(first[-100:]))),.0001)
        self.assertEqual(len(pcm(first)),len(first)*2)

    def test_audio_export_rejects_clipping_and_nonfinite(self):
        for value in [np.array([1.01]),np.array([float('nan')]),np.zeros((2,2))]:
            with self.assertRaises(ValueError):pcm(value)
