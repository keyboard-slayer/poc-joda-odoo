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
    eevil = 4

    _secret_stuff = "1+1=3"

    def tell_me_hi(self):
        return self.a

    def gift_of_satan(self):
        return 666

    def gather_secret(self):
        return self._secret_stuff

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
    safe_type = (str, int, type(None), type(range(0)), Good, type(lambda x: x), ReadOnlyObject)

    if type(value) not in safe_type and not (hasattr(value, "__self__") and type(value.__self__) in safe_type):
        raise ValueError(f"safe_eval didn't like {value}")
    else:
        return value


def ast_get_attr(obj, key, value):
    if key not in {"a", "x", "tell_me_hi", "set_x_value"}:
        raise ValueError(f"safe_eval doesn't permit you to read {key}")

    return value


class TestFuncChecker(unittest.TestCase):
    def test_function_call(self):
        def abc(a, b, c):
            return f"A: {a}, B: {b}, C: {c}"

        code = cleandoc(
            """
            abc('aaa', 'bbb', 'ccc')
            """
        )

        eval(compile(expr_checker(code, ast_get_attr), "", "exec"))

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            code = cleandoc(
                """
                abc(a='aaa', c='ccc', b=Dangerous())
                """
            )
            exec(expr_checker(code, ast_get_attr, check_type=check_type))

    def test_comp_expr(self):
        code = cleandoc(
            """
            assert([(lambda x: x**2)(n) for n in range(1, 11)] == [1, 4, 9, 16, 25, 36, 49, 64, 81, 100])
            """
        )

        exec(expr_checker(code, ast_get_attr, check_type=check_type))

    def test_attribute(self):
        a = Good()
        exec(expr_checker("a.a", ast_get_attr, check_type=check_type))
        exec(expr_checker("a.tell_me_hi()", ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read eevil"):
            exec(expr_checker("a.eevil", ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read gather_secret"):
            exec(expr_checker("a.gather_secret()", ast_get_attr, check_type=check_type))

    # FIXME: Need to implement ast_set_attr
    # def test_readonly_type(self):
    #     a = ReadOnlyObject(42)
    #
    #     exec(expr_checker("a.set_x_value(25)", ast_get_attr, check_type=check_type))
    #
    #     self.assertEqual(a.x, 42)

    def test_delete_attr(self):
        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to delete attributes"):
            exec(expr_checker("del a.x", ast_get_attr, check_type=check_type))

    def test_method_return(self):
        exec(expr_checker("Good().tell_me_hi()", ast_get_attr, check_type=check_type)),

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read gift_of_satan"):
            exec(expr_checker("Good().gift_of_satan()", ast_get_attr, check_type=check_type))

    def test_object_with(self):
        code = cleandoc(
            """
            with Good() as g:
                g.tell_me_hi()
            """
        )

        exec(expr_checker(code, ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read gift_of_satan"):
            code = cleandoc(
                """
                with Good() as g:
                    g.gift_of_satan()
                """
            )
            exec(expr_checker(code, ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            code = cleandoc(
                """
                with Dangerous() as d:
                    pass
                """
            )
            exec(expr_checker(code, ast_get_attr, check_type=check_type))

    def test_function_return(self):
        def foo():
            return Good()

        def anti_foo():
            return Dangerous()

        exec(expr_checker("foo()", ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            exec(expr_checker("anti_foo()", ast_get_attr, check_type=check_type))

    def test_evil_decorator(self):
        def evil(func):
            return lambda: Dangerous()

        @evil
        def foo():
            pass

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            code = expr_checker("foo()", ast_get_attr, check_type=check_type)
            exec(code)
            print(code)

    def test_evil_exec(self):
        with self.assertRaisesRegex(ValueError, "safe_eval didn't like 3.1415"):
            exec(expr_checker("eval('3.1415')", ast_get_attr, check_type=check_type))

    def test_from_good_to_dangerous(self):
        a = Good()

        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to modify an attribute"):
            exec(expr_checker("a.__class__ = Dangerous", ast_get_attr, check_type=check_type))

    def test_hijacking_global(self):
        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to modify locals\(\) and globals\(\)"):
            exec(expr_checker("globals()['Good'] = Dangerous", ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to modify locals\(\) and globals\(\)"):
            exec(expr_checker(cleandoc("locals()['evil'] = lambda: Dangerous()"), ast_get_attr, check_type=check_type))

    def test_forbidden_attr(self):
        a = Good()

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read _secret_stuff"):
            exec(expr_checker("print(a._secret_stuff)", ast_get_attr, check_type=check_type))

        # FIXME with ast_set_attr
        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to modify an attribute"):
            exec(expr_checker("a._secret_stuff = 42", ast_get_attr, check_type=check_type))

    def test_dangerous_lambda(self):
        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <class '__main__.Dangerous'>"):
            exec(expr_checker("(lambda: print(Dangerous()))()", ast_get_attr, check_type=check_type))

    def test_multiline(self):
        code = cleandoc(
            """
            def b():
                print('.', end='')

            b()
            """
        )

        exec(expr_checker(code, ast_get_attr, check_type=check_type))

    def test_file_open(self):
        a = Good()
        a.evil = open("test.py")

        # FIXME with ast_set_attr
        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read evil"):
            exec(expr_checker("print(a.evil)", ast_get_attr, check_type=check_type))

        a.evil.close()

    def test_overwrite(self):
        a = Good()

        with self.assertRaisesRegex(NameError, "safe_eval: check_type is a reserved name"):
            code = cleandoc(
                """
                def check_type(t):
                    return t

                c = a.evil
                """
            )

            exec(expr_checker(code, ast_get_attr, check_type=check_type))

        with self.assertRaisesRegex(NameError, "safe_eval: check_type is a reserved name"):
            code = cleandoc(
                """
                check_type = lambda t: t
                c = a.evil
                """
            )

            exec(expr_checker(code, ast_get_attr, check_type=check_type))

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
        exec(expr_checker(code, ast_get_attr, check_type=check_type2))

        with self.assertRaisesRegex(ValueError,
                                    "safe_eval didn't like <__main__.TestFuncChecker.test_isinstance_bad_idea.<locals"
                                    ">.Dangerous2 object at .+>"):
            # This doesn't 
            exec(expr_checker(code, ast_get_attr, check_type=check_type))

    def test_deny_function_call(self):
        with self.assertRaises(Exception) as e:
            exec(expr_checker("print('Hello, World')", ast_get_attr, allow_function_calls=False))

        self.assertEqual(e.exception.args[0], "safe_eval didn't permit you to call any functions")

        with self.assertRaises(Exception) as e:
            exec(expr_checker("kanban.get('sold')", ast_get_attr, allow_function_calls=False))

        self.assertEqual(e.exception.args[0], "safe_eval didn't permit you to call any functions")


if __name__ == "__main__":
    unittest.main()
