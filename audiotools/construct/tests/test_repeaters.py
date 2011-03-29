import unittest

from construct import UBInt8
from construct import Repeater
from construct import StrictRepeater, GreedyRepeater, OptionalGreedyRepeater
from construct import ArrayError, RangeError

class TestRepeater(unittest.TestCase):

    def setUp(self):
        self.c = Repeater(3, 7, UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02\x03"), [1, 2, 3])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4, 5, 6])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06\x07"),
            [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06\x07\x08\x09"),
            [1, 2, 3, 4, 5, 6, 7])

    def test_build(self):
        self.assertEqual(self.c.build([1, 2, 3, 4]), "\x01\x02\x03\x04")

    def test_build_undersized(self):
        self.assertRaises(RangeError, self.c.build, [1, 2])

    def test_build_oversized(self):
        self.assertRaises(RangeError, self.c.build, [1, 2, 3, 4, 5, 6, 7, 8])

class TestStrictRepeater(unittest.TestCase):

    def setUp(self):
        self.c = StrictRepeater(4, UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02\x03\x04"), [1, 2, 3, 4])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4])

    def test_build(self):
        self.assertEqual(self.c.build([5, 6, 7, 8]), "\x05\x06\x07\x08")

    def test_build_oversized(self):
        self.assertRaises(ArrayError, self.c.build, [5, 6, 7, 8, 9])

    def test_build_undersized(self):
        self.assertRaises(ArrayError, self.c.build, [5, 6, 7])

class TestGreedyRepeater(unittest.TestCase):

    def setUp(self):
        self.c = GreedyRepeater(UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_empty_parse(self):
        self.assertRaises(RangeError, self.c.parse, "")

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01"), [1])
        self.assertEqual(self.c.parse("\x01\x02\x03"), [1, 2, 3])
        self.assertEqual(self.c.parse("\x01\x02\x03\x04\x05\x06"),
            [1, 2, 3, 4, 5, 6])

    def test_empty_build(self):
        self.assertRaises(RangeError, self.c.build, [])

    def test_build(self):
        self.assertEqual(self.c.build([1, 2]), "\x01\x02")

class TestOptionalGreedyRepeater(unittest.TestCase):

    def setUp(self):
        self.c = OptionalGreedyRepeater(UBInt8("foo"))

    def test_trivial(self):
        pass

    def test_empty_parse(self):
        self.assertEqual(self.c.parse(""), [])

    def test_parse(self):
        self.assertEqual(self.c.parse("\x01\x02"), [1, 2])

    def test_empty_build(self):
        self.assertEqual(self.c.build([]), "")

    def test_build(self):
        self.assertEqual(self.c.build([1, 2]), "\x01\x02")
