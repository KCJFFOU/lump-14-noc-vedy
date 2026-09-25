"""Offline regression tests for LUMP-14 decision core (no model/network required)."""
import math
import sys
from unittest.mock import MagicMock
sys.modules.setdefault("stanza", MagicMock())
import unittest
from unittest.mock import patch
import LUMP14_aplikace as lump

class DecisionTests(unittest.TestCase):
    def empty(self):
        return {k: None for k in lump.FEATURES}

    def activate(self, *names):
        v = self.empty()
        for name in names:
            v[name] = lump.FEATURES[name][2]
        return v

    def test_parameters(self):
        self.assertEqual(len(lump.FEATURES), 14)
        self.assertEqual(lump.MIN_ACTIVE, 3)
        self.assertEqual(lump.P2, 0.39055351875803324)
        self.assertNotIn('COFCO', lump.FEATURES)

    def test_all_youden_cutoffs_inclusive(self):
        for name, (_, _, cutoff) in lump.FEATURES.items():
            with self.subTest(name=name):
                result = lump.score(self.activate(name))
                row = next(r for r in result['features'] if r['feature'] == name)
                self.assertTrue(row['active'])
                below = self.empty()
                below[name] = math.nextafter(cutoff, -math.inf)
                row_below = next(r for r in lump.score(below)['features'] if r['feature'] == name)
                self.assertFalse(row_below['active'])

    def test_minimum_three(self):
        for names in [(), ('conj_rel',), ('conj_rel','noun_rel')]:
            r = lump.score(self.activate(*names))
            self.assertIsNone(r['score'])
            self.assertIsNone(r['prediction'])
        r = lump.score(self.activate('conj_rel','noun_rel','pub_score'))
        self.assertEqual(r['active_n'], 3)
        self.assertIsNotNone(r['score'])

    def test_exact_p2_inclusive(self):
        values = self.activate('conj_rel','noun_rel','pub_score')
        baseline = lump.score(values)['score']
        with patch.object(lump, 'P2', baseline):
            self.assertEqual(lump.score(values)['prediction'], 'FLAWED')
        with patch.object(lump, 'P2', math.nextafter(baseline, math.inf)):
            self.assertEqual(lump.score(values)['prediction'], 'SOUND')

    def test_missing_nan_and_infinite_are_inactive(self):
        v = self.empty()
        v.update(conj_rel=float('nan'), noun_rel=float('inf'), pub_score=-float('inf'))
        r = lump.score(v)
        self.assertEqual(r['active_n'], 0)
        self.assertIsNone(r['prediction'])

    def test_reference_articles(self):
        cases = [
            (('noun_rel','prep_rel','num_rel','pub_score'), 'SOUND', -1.0, 0, 4),
            (('adv_rel','conj_rel','pron_rel','part_rel','dat_rel','dem_pron_rel','fic_score','MDD','MHD'), 'FLAWED', 1.0, 9, 0),
            (('pron_rel','num_rel','fic_score','adv_rel','dem_pron_rel','part_rel','dat_rel'), 'FLAWED', 0.6699486991377446, 6, 1),
        ]
        for names, prediction, expected, red, green in cases:
            with self.subTest(prediction=prediction, names=names):
                r = lump.score(self.activate(*names))
                self.assertEqual(r['prediction'], prediction)
                self.assertAlmostEqual(r['score'], expected, places=12)
                self.assertEqual(sum(x['active'] and x['favored']=='FLAWED' for x in r['features']), red)
                self.assertEqual(sum(x['active'] and x['favored']=='SOUND' for x in r['features']), green)

if __name__ == '__main__':
    unittest.main(verbosity=2)
