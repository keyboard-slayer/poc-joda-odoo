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


def check_type(method, value):
    safe_type = (str, int, type(None), type(range(0)), Good)

    if type(value) in (list, tuple, set):
        for val in value:
            check_type(method, val)
        return value
    elif type(value) not in safe_type:
        raise ValueError(f"safe_eval didn't like {value}")
    else:
        return value


_ALLOWED_ATTR = {"a", "x", "tell_me_hi", "set_x_value"}


class TestFuncChecker(unittest.TestCase):
    def test_function_call(self):
        def abc(a, b, c):
            return f"A: {a}, B: {b}, C: {c}"

        ret = eval(compile(expr_checker(
            "abc('aaa', 'bbb', 'ccc')", _ALLOWED_ATTR, {}), "", "exec"))

        with self.assertRaises(ValueError):
            exec(expr_checker("abc(a='aaa', c='ccc', b=Dangerous())",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_comp_expr(self):
        exec(expr_checker(
            "[(lambda x: x**2)(n) for n in range(1, 11)]", _ALLOWED_ATTR, {}, check_type=check_type)),

    def test_attribute(self):
        a = Good()
        exec(expr_checker("a.a", _ALLOWED_ATTR, {}, check_type=check_type))
        exec(expr_checker("a.tell_me_hi()", _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a.evil", _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a.gather_secret()",
                _ALLOWED_ATTR, {}, check_type=check_type))

    def test_reaonly_type(self):
        a = ReadOnlyObject(42)

        exec(expr_checker("a.set_x_value(25)",
            _ALLOWED_ATTR, {ReadOnlyObject}))

        exec(expr_checker("a.x = 99", _ALLOWED_ATTR, {ReadOnlyObject}))
        self.assertEqual(a.x, 42)

    def test_delete_attr(self):
        with self.assertRaises(ValueError):
            exec(expr_checker("del a.x", _ALLOWED_ATTR, {}, check_type=check_type))

    def test_method_return(self):
        exec(expr_checker("Good().tell_me_hi()",
            _ALLOWED_ATTR, {}, check_type=check_type)),

        with self.assertRaises(ValueError):
            exec(expr_checker("Good().gift_of_satan()",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_object_with(self):
        exec(expr_checker(cleandoc("""
            with Good() as g:
                g.tell_me_hi()"""), _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker(cleandoc("""
                with Good() as g:
                    g.gift_of_satan()"""), _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker(cleandoc("""
                with Dangerous() as d:
                    pass"""), _ALLOWED_ATTR, {}, check_type=check_type))

    def test_function_return(self):
        def foo():
            return Good()

        def anti_foo():
            return Dangerous()

        exec(expr_checker("foo()", _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("anti_foo()", _ALLOWED_ATTR, {}, check_type=check_type))

    def test_evil_decorator(self):
        def evil(func):
            return lambda: Dangerous()

        @evil
        def foo():
            pass

        with self.assertRaises(ValueError):
            exec(expr_checker("foo()", _ALLOWED_ATTR, {}, check_type=check_type))

    def test_evil_exec(self):
        with self.assertRaises(ValueError):
            exec(expr_checker("eval('3.1415')",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_from_good_to_dangerous(self):
        a = Good()

        with self.assertRaises(ValueError):
            exec(expr_checker("a.__class__ = Dangerous",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_hijacking_global(self):
        with self.assertRaises(ValueError):
            exec(expr_checker(
                "globals()['Good'] = Dangerous", _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker(
                "globals()['evil'] = lambda: Dangerous()", _ALLOWED_ATTR, {}, check_type=check_type))

    def test_forbidden_attr(self):
        a = Good()

        with self.assertRaises(ValueError):
            exec(expr_checker("print(a._secret_stuff)",
                 _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a._secret_stuff = 42",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_dangerous_lambda(self):
        with self.assertRaises(ValueError):
            exec(expr_checker("(lambda: print(Dangerous()))()",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_multiline(self):
        code = cleandoc("""
            def b():
                print('.', end='')

            b()
        """)

        exec(expr_checker(code, _ALLOWED_ATTR, {}, check_type=check_type))

    def test_file_open(self):
        a = Good()
        a.evil = open("test.py")

        with self.assertRaises(ValueError):
            exec(expr_checker("print(a.evil)",
                 _ALLOWED_ATTR, {}, check_type=check_type))

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

        with self.assertRaises(NameError):
            exec(expr_checker(code, _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(NameError):
            exec(expr_checker(code2, _ALLOWED_ATTR, {}, check_type=check_type))

    def test_collections(self):
        def a(a):
            return a

        exec(expr_checker("a([1, Good(), 3])",
             _ALLOWED_ATTR, {}, check_type=check_type))
        exec(expr_checker("a((4, 5, 6))", _ALLOWED_ATTR, {}, check_type=check_type))
        exec(expr_checker("a({7, 'hi', None})",
             _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a([1.5, 2, 3])",
                 _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a((4, Dangerous(), 'lol'))",
                 _ALLOWED_ATTR, {}, check_type=check_type))

        with self.assertRaises(ValueError):
            exec(expr_checker("a({4, 3.1415, 3})",
                 _ALLOWED_ATTR, {}, check_type=check_type))

    def test_isinstance_bad_idea(self):
        class Dangerous2(Good):
            pass

        def check_type2(method, value):
            safe_type = (str, int, type(None), type(range(0)), Good)

            if isinstance(value, (list, tuple, set)):
                for val in value:
                    check_type(method, val)
                return value
            elif not isinstance(value, safe_type):
                raise ValueError(f"safe_eval didn't like {value}")
            else:
                return value

        code = "(1, 'Hi', Dangerous2())"

        # This pass
        exec(expr_checker(code, _ALLOWED_ATTR, {}, check_type=check_type2))

        with self.assertRaises(ValueError):
            # This doesn't 
           exec(expr_checker(code, _ALLOWED_ATTR, {}, check_type=check_type)) 

    def test_deny_function_call(self):
        with self.assertRaises(Exception) as e:
            exec(expr_checker("print('Hello, World')", _ALLOWED_ATTR, {}, allow_function_calls=False))

        self.assertEqual(e.exception.args[0], "safe_eval didn't allow you to call any functions")

        with self.assertRaises(Exception) as e:
            exec(expr_checker("kanban.get('sold')", _ALLOWED_ATTR, {}, allow_function_calls=False))

        self.assertEqual(e.exception.args[0], "safe_eval didn't allow you to call any functions")

if __name__ == "__main__":
    unittest.main()
