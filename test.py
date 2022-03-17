#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from inspect import cleandoc
from expr_checker import *

class Dangerous:
    pass

class Good:
    a = "hi"
    evil = Dangerous()

    _secret_stuff = "1+1=3"

    def tell_me_hi(self):
        return self.a
    
    def __enter__(self):
        return Good()

    def __exit__(self, exec_type, exec_value, traceback):
        pass


class ReadOnlyObject:
    def __init__(self, x):
        self.set_x_value(x)

    def set_x_value(self, x):
        self.x = x


_WHITELIST = {str, int, type(None), Good, type(range(0))}
_ALLOWED_ATTR = {"a", "x", "tell_me_hi", "set_x_value"}


class TestFuncChecker(unittest.TestCase):
    def test_function_call(self):
        def abc(a, b, c):
            return f"A: {a}, B: {b}, C: {c}"

        self.assertEqual(
            eval(expr_checker("abc('aaa', 'bbb', 'ccc')",
                 _WHITELIST, _ALLOWED_ATTR, {})),
            "A: aaa, B: bbb, C: ccc"
        )

        with self.assertRaises(ValueError):
            eval(expr_checker("abc(a='aaa', c='ccc', b=Dangerous())",
                 _WHITELIST, _ALLOWED_ATTR, {}))

    def test_comp_expr(self):
        self.assertEqual(
            eval(expr_checker(
                "[(lambda x: x**2)(n) for n in range(1, 11)]", _WHITELIST, _ALLOWED_ATTR, {})),
            [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
        )

    def test_attribute(self):
        a = Good()
        eval(expr_checker("a.a", _WHITELIST, _ALLOWED_ATTR, {}))
        eval(expr_checker("a.tell_me_hi()", _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            eval(expr_checker("a.evil", _WHITELIST, _ALLOWED_ATTR, {}))
            
        with self.assertRaises(ValueError):
            eval(expr_checker("a.gather_secret()", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_reaonly_type(self):
        a = ReadOnlyObject(42)

        eval(expr_checker("a.set_x_value(25)",
             _WHITELIST, _ALLOWED_ATTR, {ReadOnlyObject}))
        exec(expr_checker("a.x = 99", _WHITELIST,
             _ALLOWED_ATTR, {ReadOnlyObject}))

        self.assertEqual(a.x, 42)

    def test_method_return(self):
        self.assertEqual(
            eval(expr_checker("Good().tell_me_hi()",
                 _WHITELIST, _ALLOWED_ATTR, {})),
            "hi"
        )

        with self.assertRaises(ValueError):
            eval(expr_checker("Good().gift_of_satan()",
                 _WHITELIST, _ALLOWED_ATTR, {}))

    def test_object_with(self):
        exec(expr_checker(cleandoc("""
            with Good() as g:
                g.tell_me_hi()"""), _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker(cleandoc("""
                with Good() as g:
                    g.gift_of_satan()"""), _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker(cleandoc("""
                with Dangerous() as d:
                    pass"""), _WHITELIST, _ALLOWED_ATTR, {}))

    def test_function_return(self):
        def foo():
            return Good()

        def anti_foo():
            return Dangerous()

        eval(expr_checker("foo()", _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            eval(expr_checker("anti_foo()", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_evil_decorator(self):
        def evil(func):
            return lambda: Dangerous()

        @evil
        def foo():
            pass

        with self.assertRaises(ValueError):
            eval(expr_checker("foo()", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_evil_eval(self):
        with self.assertRaises(ValueError):
            eval(expr_checker("eval('3.1415')", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_from_good_to_dangerous(self):
        a = Good()

        with self.assertRaises(ValueError):
            exec(expr_checker("a.__class__ = Dangerous",
                 _WHITELIST, _ALLOWED_ATTR, {}))

    def test_hijacking_global(self):
        with self.assertRaises(ValueError):
            exec(expr_checker(
                "globals()['Good'] = Dangerous", _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker(
                "globals()['evil'] = lambda: Dangerous()", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_forbidden_attr(self):
        a = Good()

        with self.assertRaises(ValueError):
            exec(expr_checker("print(a._secret_stuff)",
                 _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker("a._secret_stuff = 42", _WHITELIST, _ALLOWED_ATTR, {}))

    def test_dangerous_lambda(self):
        with self.assertRaises(ValueError):
            exec(expr_checker("(lambda: print(Dangerous()))()",
                 _WHITELIST, _ALLOWED_ATTR, {}))

    def test_multiline(self):
        code = cleandoc("""
            def b():
                print('.', end='')

            b()
        """)

        exec(expr_checker(code, _WHITELIST, _ALLOWED_ATTR, {}))

    def test_file_open(self):
        a = Good()
        a.evil = open("test.py")

        with self.assertRaises(ValueError):
            exec(expr_checker("print(a.evil)", _WHITELIST, _ALLOWED_ATTR, {}))

        a.evil.close()

    def test_overwrite(self):
        a = Good()

        code = cleandoc("""
                def check_type(t):
                    return t
                
                c = a.evil""")

        code2 = cleandoc("""
                check_type = lambda t: t
                c = a.evil""")

        _ALLOWED_ATTR.add("evil")
        _WHITELIST.add(type(lambda x: x))

        with self.assertRaises(NameError):
            exec(expr_checker(code, _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(NameError):
            exec(expr_checker(code2, _WHITELIST, _ALLOWED_ATTR, {}))
    
    def test_collections(self):
        def a(a):
            return a
    
        exec(expr_checker("a([1, Good(), 3])", _WHITELIST, _ALLOWED_ATTR, {}))
        exec(expr_checker("a((4, 5, 6))", _WHITELIST, _ALLOWED_ATTR, {}))
        exec(expr_checker("a({7, 'hi', None})", _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker("a([1.5, 2, 3])", _WHITELIST, _ALLOWED_ATTR, {}))

        with self.assertRaises(ValueError):
            exec(expr_checker("a((4, Dangerous(), 'lol'))", _WHITELIST, _ALLOWED_ATTR, {}))
            
        with self.assertRaises(ValueError):
            exec(expr_checker("a({4, 3.1415, 3})", _WHITELIST, _ALLOWED_ATTR, {}))


if __name__ == "__main__":
    unittest.main()
