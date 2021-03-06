""" 
:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2018-03-12
:Copyright: 2018, Karr Lab
:License: MIT
"""

import types
import unittest
import wc_utils


class ApiTestCase(unittest.TestCase):
    def test(self):
        self.assertIsInstance(wc_utils.workbook, types.ModuleType)
        self.assertIsInstance(wc_utils.workbook.Workbook, type)
