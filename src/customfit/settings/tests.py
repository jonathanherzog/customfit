import os

from django.test import TestCase

from .base import bool_from_env

FOO = "FOO"


class BoolFromEnvTests(TestCase):

    def setUp(self):
        self.assertNotIn(FOO, os.environ)

    def tearDown(self):
        if FOO in os.environ:
            del os.environ[FOO]

    def test_error_case(self):
        with self.assertRaises(AssertionError):
            bool_from_env(FOO, 10)

        with self.assertRaises(AssertionError):
            bool_from_env(FOO, "True")

    def test_true(self):
        os.environ[FOO] = "True"
        self.assertTrue(bool_from_env(FOO, True))
        self.assertTrue(bool_from_env(FOO, False))
        self.assertTrue(bool_from_env(FOO, 1))
        self.assertTrue(bool_from_env(FOO, 0))

        os.environ[FOO] = "1"
        self.assertTrue(bool_from_env(FOO, True))
        self.assertTrue(bool_from_env(FOO, False))
        self.assertTrue(bool_from_env(FOO, 1))
        self.assertTrue(bool_from_env(FOO, 0))

    def test_false(self):
        os.environ[FOO] = "FALSE"
        self.assertFalse(bool_from_env(FOO, True))
        self.assertFalse(bool_from_env(FOO, False))
        self.assertFalse(bool_from_env(FOO, 1))
        self.assertFalse(bool_from_env(FOO, 0))

        os.environ[FOO] = "0"
        self.assertFalse(bool_from_env(FOO, True))
        self.assertFalse(bool_from_env(FOO, False))
        self.assertFalse(bool_from_env(FOO, 1))
        self.assertFalse(bool_from_env(FOO, 0))

    def test_undefined1(self):
        self.assertTrue(bool_from_env(FOO, True))
        self.assertFalse(bool_from_env(FOO, False))
        self.assertTrue(bool_from_env(FOO, 1))
        self.assertFalse(bool_from_env(FOO, 0))

    def test_undefined2(self):
        os.environ[FOO] = ""
        self.assertTrue(bool_from_env(FOO, True))
        self.assertFalse(bool_from_env(FOO, False))
        self.assertTrue(bool_from_env(FOO, 1))
        self.assertFalse(bool_from_env(FOO, 0))
