#!/usr/bin/env python
# encoding: utf-8

import logging
from collections import namedtuple
from functools import wraps

__all__ = ("AllowFailResult", "AllowFail")


AllowFailResult = namedtuple(
    "AllowFailResult", ["ok", "result"])


class AllowFail(object):
    logger = logging.getLogger("OnError")

    def __init__(self, label, *params, **options):
        self.label = label
        self.params = params
        self.error_handler = options.pop("on_error", self.on_error)
        self.logger = options.pop("logger", self.logger)

    def on_error(self, label, err):
        """On error handler
        """
        self.logger.warning("%s got an error: %s", label, err)

    def __enter__(self):
        """Use instance as a context manager to protect a block
        """
        return self

    def __exit__(self, typ, val, trbk):
        """Catch exceptions
        """
        if typ:
            if val is None:
                val = typ()
            self.error_handler(self.label % self.params, val)

        # catch exceptions
        return True

    def __call__(self, func):
        """Use instance as a decorator to protect a function call
        """
        @wraps(func)
        def protect(*args, **kwg):
            try:
                result = AllowFailResult(ok=True, result=func(*args, **kwg))
            except Exception as err:
                result = AllowFailResult(ok=False, result=err)

                f_name = str(func)
                if hasattr(func, "__name__"):
                    f_name = func.__name__
                elif hasattr(func, "func_name"):
                    f_name = func.func_name

                with AllowFail("On error handler: %s", f_name):
                    self.error_handler(self.label % self.params, err)

            return result
        return protect


import unittest


class TestUsage(unittest.TestCase):
    def setUp(self):
        self.cache = []

    def log(self, *args, **kwg):
        self.cache.append({
            "args": args,
            "kwg": kwg})

    def test_decorator(self):
        @AllowFail("test %s", "valueerror", on_error=self.log)
        def valueerror():
            raise ValueError("test exception")

        @AllowFail("test %s", "func", on_error=self.log)
        def func():
            return 1

        res = valueerror()
        self.assertFalse(res.ok)
        self.assertEqual(res.result.message, "test exception")
        log = self.cache.pop()
        self.assertEqual(log["args"][0], "test valueerror")
        self.assertEqual(log["args"][1], res.result)

        res = func()
        self.assertTrue(res.ok)
        self.assertEqual(res.result, 1)
        self.assertListEqual(self.cache, [])

    def test_contextmanager(self):
        with AllowFail("test %s", "contextmanager", on_error=self.log):
            raise ValueError()

        log = self.cache.pop()
        self.assertEqual(log["args"][0], "test contextmanager")
        self.assertTrue(isinstance(log["args"][1], ValueError))


if __name__ == "__main__":
    unittest.main()
