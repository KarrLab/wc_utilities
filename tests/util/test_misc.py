'''Test misc

:Author: Arthur Goldberg, Arthur.Goldberg@mssm.edu
:Date: 2016-12-10
:Copyright: 2016, Karr Lab
:License: MIT
'''

import unittest
from wc_utils.util.misc import get_most_qual_cls_name
from wc_utils.util.stats import ExponentialMovingAverage

class C(object):
    class D(object):
        pass
d=C.D()

class TestMisc(unittest.TestCase):

    def test_get_qual_name(self):
    
        ema = ExponentialMovingAverage(1, .5)
        self.assertEqual(get_most_qual_cls_name(self), 'tests.util.test_misc.TestMisc')
        self.assertEqual(get_most_qual_cls_name(TestMisc), 'tests.util.test_misc.TestMisc')
        self.assertEqual(get_most_qual_cls_name(ema),
            'wc_utils.util.stats.ExponentialMovingAverage')
        self.assertEqual(get_most_qual_cls_name(ExponentialMovingAverage),
            'wc_utils.util.stats.ExponentialMovingAverage')
            
        try:
            # Fully qualified class names are available for Python >= 3.3.
            hasattr(self, '__qualname__')
            self.assertEqual(get_most_qual_cls_name(d), 'tests.util.test_misc.C.D')
        except:
            self.assertEqual(get_most_qual_cls_name(d), 'tests.util.test_misc.D')
