import unittest

from util import strip_new_line


class UtilTest(unittest.TestCase):

    def test_strip_new_line_should_remove_strip_line_markers(self):
        self.assertEqual('7 2 0 1', strip_new_line('7 2 0 1\r\n'))
        self.assertEqual('7 2 0 1', strip_new_line('7 2 0 1\r'))
        self.assertEqual('7 2 0 1', strip_new_line('7 2 0 1\n'))
        self.assertEqual('7 2\r\n 0 1', strip_new_line('7 2\r\n 0 1\r\n'))

        self.assertEqual('', strip_new_line(''))
        self.assertEqual('', strip_new_line('\r'))
        self.assertEqual('', strip_new_line('\r\n'))
        self.assertEqual('', strip_new_line('\n'))

        self.assertEqual(None, strip_new_line(None))
