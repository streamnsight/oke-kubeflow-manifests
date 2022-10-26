import unittest
import sys
import os

dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(dir)

from cli.src import okf


class DependenciesValidatorTestCase(unittest.TestCase):

    def setUp(self):
        self.dv = okf.DependenciesValidator()
        pass

    def tearDown(self):
        pass

    def test_parse_versions_file(self):
        print(self.dv.versions)
        pass


if __name__ == '__main__':
    unittest.main()