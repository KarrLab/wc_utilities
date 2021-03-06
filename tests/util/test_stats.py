""" Statistic utilities tests

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2017-05-26
:Copyright: 2017-2018, Karr Lab
:License: MIT
"""

from wc_utils.util import stats
import numpy
import numpy.testing
import unittest


class TestStats(unittest.TestCase):

    def test_exponential_moving_average(self):
        exp = stats.ExponentialMovingAverage(1., alpha=0.)
        self.assertEqual(exp.value, 1.)
        self.assertEqual(exp.alpha, 0.)

        exp = stats.ExponentialMovingAverage(1., center_of_mass=0.)
        self.assertEqual(exp.value, 1.)
        self.assertEqual(exp.alpha, 1.)

        exp = stats.ExponentialMovingAverage(1., alpha=0.)
        self.assertEqual(exp.add_value(2), 1.)
        self.assertEqual(exp.add_value(3), 1.)

        exp = stats.ExponentialMovingAverage(1., alpha=1.)
        self.assertEqual(exp.add_value(2), 2.)
        self.assertEqual(exp.add_value(3), 3.)

        exp = stats.ExponentialMovingAverage(1., alpha=0.5)
        self.assertEqual(exp.add_value(2), 1.5)
        self.assertEqual(exp.add_value(3), 2.25)

        exp = stats.ExponentialMovingAverage(1., alpha=0.5)
        self.assertEqual(exp.get_ema(), 1.)

        exp2 = stats.ExponentialMovingAverage(1., alpha=0.5)
        self.assertEqual(exp, exp2)
        # alpha =  1/(1 + center_of_mass) <=> center_of_mass =  (1/alpha) - 1
        self.assertEqual(exp, stats.ExponentialMovingAverage(1., center_of_mass=1))

        self.assertNotEqual(exp, object())
        self.assertNotEqual(object(), exp)
        exp2.add_value(3)
        self.assertNotEqual(exp, exp2)
        self.assertNotEqual(exp, stats.ExponentialMovingAverage(1., alpha=0.6))

        with self.assertRaisesRegex(ValueError, '^Only one of `alpha` or `center_of_mass` should be provided$'):
            stats.ExponentialMovingAverage(1., alpha=0.5, center_of_mass=0.)

        with self.assertRaisesRegex(ValueError, '^`alpha` or `center_of_mass` must be provided$'):
            stats.ExponentialMovingAverage(1.)

        with self.assertRaisesRegex(ValueError, '^`alpha` must satisfy 0 <= `alpha` <= 1: '):
            stats.ExponentialMovingAverage(1., alpha=-.1)

        with self.assertRaisesRegex(ValueError, '^`alpha` must satisfy 0 <= `alpha` <= 1: '):
            stats.ExponentialMovingAverage(1., center_of_mass=-2.)

        # test sequences of averages that have simple analyic solutions
        x = 2**10
        ema = stats.ExponentialMovingAverage(x, center_of_mass=1)
        self.assertEqual(x, ema.get_ema())
        for i in range(10):
            self.assertEqual(x, ema.add_value(x))
        ema = stats.ExponentialMovingAverage(x, alpha=0.75)
        for i in range(10):
            self.assertEqual(x, ema.add_value(x))

    def test_weighted_mean(self):
        self.assertEqual(stats.weighted_mean([2, 1], [1, 1]), 1.5)
        self.assertEqual(stats.weighted_mean([2, 1], [0, 1]), 1.0)
        self.assertEqual(stats.weighted_mean([2, 1], [1, 0]), 2.0)

        numpy.testing.assert_equal(stats.weighted_mean([], []), numpy.nan)

        numpy.testing.assert_equal(stats.weighted_mean([1, 2], [1, numpy.nan]), 1)
        numpy.testing.assert_equal(stats.weighted_mean([1, 2], [numpy.nan, numpy.nan]), numpy.nan)
        numpy.testing.assert_equal(stats.weighted_mean([1, 2], [1, numpy.nan], ignore_nan=False), numpy.nan)

    def test_weighted_percentile(self):
        self.assertEqual(stats.weighted_percentile([2], [1], 0), 2.)
        self.assertEqual(stats.weighted_percentile([2], [1], 50), 2.)
        self.assertEqual(stats.weighted_percentile([2], [1], 100), 2.)

        self.assertEqual(stats.weighted_percentile([2, 1], [1, 1], 0), 1.)
        self.assertEqual(stats.weighted_percentile([2, 1], [1, 1], 25), 1.)
        self.assertEqual(stats.weighted_percentile([2, 1], [1, 1], 50), 1.5)
        self.assertEqual(stats.weighted_percentile([2, 1], [1, 1], 75), 2.)
        self.assertEqual(stats.weighted_percentile([2, 1], [1, 1], 100), 2.)

        self.assertEqual(stats.weighted_percentile([2, 1], [10, 1], 20), 2.)
        self.assertEqual(stats.weighted_percentile([2, 1], [1, 10], 60), 1.)

        self.assertEqual(stats.weighted_percentile([2, 1, 3], [1, 1, 1], 0), 1)
        self.assertEqual(stats.weighted_percentile([2, 1, 3], [1, 1, 1], 20), 1)
        self.assertEqual(stats.weighted_percentile([2, 1, 3], [1, 1, 1], 50), 2)
        self.assertEqual(stats.weighted_percentile([2, 1, 3], [1, 1, 1], 80), 3)
        self.assertEqual(stats.weighted_percentile([2, 1, 3], [1, 1, 1], 100), 3)

        self.assertEqual(stats.weighted_percentile([2, 1], [1, 0], 50), 2)
        numpy.testing.assert_equal(stats.weighted_percentile([2, 1], [0, 0], 100), float('nan'))

        numpy.testing.assert_equal(stats.weighted_percentile([1, 2, 3, 0], [10, 1, 20, numpy.nan], 0), 1)
        numpy.testing.assert_equal(stats.weighted_percentile([1, 2, 3, 0], [10, 1, 20, numpy.nan], 100), 3)
        numpy.testing.assert_equal(stats.weighted_percentile([1, 2, 3, 0], [10, 1, 20, numpy.nan], 0, ignore_nan=False), numpy.nan)
        numpy.testing.assert_equal(stats.weighted_percentile([1, 2, 3, 0], [10, 1, 20, numpy.nan], 100, ignore_nan=False), numpy.nan)

    def test_weighted_median(self):
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 1, 1]), numpy.median([2., 1., 3.]))
        self.assertEqual(stats.weighted_median([2, 1, 3, 4], [1, 1, 1, 1]), numpy.median([2., 1., 3., 4.]))

        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 0, 0]), 2.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [0, 1, 0]), 1.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [0, 0, 1]), 3.0)

        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 1, 0]), 1.5)
        self.assertEqual(stats.weighted_median([2, 1, 3], [0, 1, 1]), 2.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 0, 1]), 2.5)

        self.assertEqual(stats.weighted_median([2, 1, 3], [2, 1, 1]), 2.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 1, 2]), 2.5)
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 2, 1]), 1.5)

        self.assertEqual(stats.weighted_median([2, 1, 3], [3, 1, 1]), 2.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 1, 3]), 3.0)
        self.assertEqual(stats.weighted_median([2, 1, 3], [1, 3, 1]), 1.0)

        self.assertEqual(stats.weighted_median([2, 1], [1, 1]), 1.5)
        self.assertEqual(stats.weighted_median([2, 1], [2, 1]), 2.0)
        self.assertEqual(stats.weighted_median([2, 1], [1, 2]), 1.0)

        numpy.testing.assert_equal(stats.weighted_median([2, 1, 3], [0, 0, 0]), float('nan'))
        numpy.testing.assert_equal(stats.weighted_median([2], [1]), 2)
        numpy.testing.assert_equal(stats.weighted_median([2], [0]), float('nan'))

        numpy.testing.assert_equal(stats.weighted_median([1, 2, 3, 0], [10, 1, 20, numpy.nan]), 3)
        numpy.testing.assert_equal(stats.weighted_median([1, 2, 3, 0], [10, 1, 20, numpy.nan], ignore_nan=False), numpy.nan)

    def test_weighted_mode(self):
        self.assertEqual(stats.weighted_mode([1], [1]), 1)

        self.assertEqual(stats.weighted_mode([1, 2], [1, 1]), 1)
        self.assertEqual(stats.weighted_mode([2, 1], [1, 1]), 1)
        self.assertEqual(stats.weighted_mode([1, 2], [1, 10]), 2)
        self.assertEqual(stats.weighted_mode([2, 1], [10, 1]), 2)

        self.assertEqual(stats.weighted_mode([1, 1, 1, 2], [1, 1, 1, 1]), 1)
        self.assertEqual(stats.weighted_mode([1, 1, 2, 2], [1, 1, 1, 1]), 1)
        self.assertEqual(stats.weighted_mode([1, 2, 2, 2], [1, 1, 1, 1]), 2)

        self.assertEqual(stats.weighted_mode([1, 2, 2, 2], [10, 1, 1, 1]), 1)
        self.assertEqual(stats.weighted_mode([1, 2, 3, 0], [10, 1, 20, 1]), 3)

        numpy.testing.assert_equal(stats.weighted_mode([1, 2, 3, 0], [0, 0, 0, 0]), float('nan'))

        numpy.testing.assert_equal(stats.weighted_mode([1, 2, 3, 0], [10, 1, 20, numpy.nan]), 3)
        numpy.testing.assert_equal(stats.weighted_mode([1, 2, 3, 0], [10, 1, 20, numpy.nan], ignore_nan=False), numpy.nan)
