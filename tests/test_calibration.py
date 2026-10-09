import unittest

from juridicator.calibration import level3_allowed, stats, wilson_lower


class CalibrationTests(unittest.TestCase):
    def test_wilson_is_below_the_raw_rate_and_tightens_with_data(self):
        self.assertLess(wilson_lower(9, 10), 0.9)
        self.assertGreater(wilson_lower(990, 1000), wilson_lower(99, 100))
        self.assertEqual(wilson_lower(0, 0), 0.0)

    def test_locked_by_default_and_for_small_samples(self):
        self.assertFalse(level3_allowed(stats([])))
        small = stats([{"ai": "clear", "label": "accept"}] * 100)
        self.assertFalse(level3_allowed(small))

    def test_one_missed_bad_case_locks_it_however_large_the_sample(self):
        rows = [{"ai": "clear", "label": "accept"}] * 2000 + [{"ai": "clear", "label": "reject"}]
        self.assertFalse(level3_allowed(stats(rows)))

    def test_opens_only_on_a_large_clean_sample(self):
        rows = [{"ai": "clear", "label": "accept"}] * 1500 + [{"ai": "concern", "label": "reject"}] * 100
        self.assertTrue(level3_allowed(stats(rows)))


if __name__ == "__main__":
    unittest.main()
