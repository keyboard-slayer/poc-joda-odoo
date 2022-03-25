#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from inspect import cleandoc

from evaluator import safe_eval
from expr_checker import __ast_default_check_type


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


class ReadOnlyObject:
    def __init__(self, x):
        self.set_x_value(x)

    def set_x_value(self, x):
        self.x = x


def check_type(method, value):
    safe_type = (Good, ReadOnlyObject)

    if type(value) in safe_type:
        return value

    return __ast_default_check_type(method, value)


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

        safe_eval(code, locals_dict={"abc": abc})

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            code = cleandoc(
                """
                abc(a='aaa', c='ccc', b=Dangerous())
                """
            )

            safe_eval(code, locals_dict={"abc": abc, "Dangerous": Dangerous})

    def test_comp_expr(self):
        code = cleandoc(
            """
            [(lambda x: x**2)(n) for n in range(1, 11)]
            """
        )
        self.assertEqual(safe_eval(code), [1, 4, 9, 16, 25, 36, 49, 64, 81, 100])

    def test_attribute(self):
        a = Good()

        safe_eval("a.a", locals_dict={"a": a})
        safe_eval("a.tell_me_hi()", locals_dict={"a": a})

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read eevil"):
            safe_eval("a.eevil", locals_dict={"a": a})

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read gather_secret"):
            safe_eval("a.gather_secret()", locals_dict={"a": a})

    # FIXME: Need to implement ast_set_attr
    # def test_readonly_type(self):
    #     a = ReadOnlyObject(42)
    #
    #     exec(expr_checker("a.set_x_value(25)", ast_get_attr, check_type=check_type))
    #
    #     self.assertEqual(a.x, 42)

    def test_delete_attr(self):
        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to delete attributes"):
            safe_eval("del a.x")

    def test_method_return(self):
        code = cleandoc(
            """
            Good().tell_me_hi()
            """
        )
        safe_eval(code, locals_dict={"Good": Good}, check_type=check_type)

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read gift_of_satan"):
            code = cleandoc(
                """
                Good().gift_of_satan()
                """
            )
            safe_eval(code, locals_dict={"Good": Good}, check_type=check_type)

    def test_function_return(self):
        def foo():
            return Good()

        def anti_foo():
            return Dangerous()

        safe_eval('foo()', locals_dict={'foo': foo}, check_type=check_type)

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            safe_eval('anti_foo()', locals_dict={'anti_foo': anti_foo}, check_type=check_type)

    def test_evil_decorator(self):
        def evil(func):
            return lambda: Dangerous()

        @evil
        def foo():
            pass

        with self.assertRaisesRegex(ValueError, "safe_eval didn't like <__main__.Dangerous object at .+>"):
            safe_eval('foo()', locals_dict={'foo': foo, 'evil': evil}, check_type=check_type)

    def test_from_good_to_dangerous(self):
        a = Good()

        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to store values in attributes"):
            safe_eval('a.__class__ = Dangerous', locals_dict={'Good': Good, 'Dangerous': Dangerous},
                      check_type=check_type)

    def test_forbidden_attr(self):
        a = Good()

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read _secret_stuff"):
            safe_eval('a._secret_stuff', locals_dict={'a': a})

        # FIXME with ast_set_attr
        with self.assertRaisesRegex(ValueError, "safe_eval: doesn't permit you to store values in attributes"):
            safe_eval('a._secret_stuff = 42', mode='exec', locals_dict={'a': a})

    def test_file_open(self):
        a = Good()
        a.evil = open("test.py")

        # FIXME with ast_set_attr
        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read evil"):
            safe_eval("print(a.evil)", locals_dict={"a": a})

        a.evil.close()

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
        safe_eval(code, locals_dict={"Dangerous2": Dangerous2}, check_type=check_type2)

        with self.assertRaisesRegex(ValueError,
                                    "safe_eval didn't like <__main__.TestFuncChecker.test_isinstance_bad_idea.<locals"
                                    ">.Dangerous2 object at .+>"):
            # This doesn't
            safe_eval(code, locals_dict={"Dangerous2": Dangerous2})

    def test_deny_function_call(self):
        with self.assertRaises(Exception) as e:
            safe_eval("print('Hello, World')", allow_functions_calls=False)

        self.assertEqual(e.exception.args[0], "safe_eval didn't permit you to call any functions")

        with self.assertRaises(Exception) as e:
            safe_eval("kanban.get('sold')", allow_functions_calls=False)

        self.assertEqual(e.exception.args[0], "safe_eval didn't permit you to call any functions")

    def test_subscript(self):
        a = [0, "Hi", Dangerous()]

        safe_eval("a[1]", locals_dict={"a": a})

        with self.assertRaisesRegex(ValueError, "<__main__.Dangerous object at .+>"):
            safe_eval("a[-1]", locals_dict={"a": a})

    def test_assign(self):
        safe_eval("a = 4", mode="exec")
        safe_eval("a, b = 4, 5", mode="exec")

        with self.assertRaisesRegex(ValueError, "<__main__.Dangerous object at .+>"):
            safe_eval("a = Dangerous()", mode="exec", locals_dict={"Dangerous": Dangerous})

        with self.assertRaisesRegex(ValueError, "<__main__.Dangerous object at .+>"):
            safe_eval("a, b = Good(), Dangerous()", mode="exec", locals_dict={"Dangerous": Dangerous, "Good": Good},
                      check_type=check_type)

    def test_dangerous_lambda(self):
        with self.assertRaisesRegex(ValueError, "<__main__.Dangerous object at .+>"):
            safe_eval("(lambda : print(Dangerous()))()", mode="exec", globals_dict={"Dangerous": Dangerous})

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

            safe_eval(code, check_type=check_type, locals_dict={"a": a}, mode="exec")

        with self.assertRaisesRegex(NameError, "safe_eval: check_type is a reserved name"):
            code = cleandoc(
                """
                check_type = lambda t: t
                c = a.evil
                """
            )

            safe_eval(code, check_type=check_type, locals_dict={"a": a}, mode="exec")

    def test_function_body(self):
        Good.test = open('test.py')
        code = cleandoc("""
               def b():
                   print(Good.test)
               b()
           """)

        with self.assertRaisesRegex(ValueError, "safe_eval doesn't permit you to read test"):
            safe_eval(code, check_type=check_type, globals_dict={"Good": Good}, mode="exec")


if __name__ == "__main__":
    unittest.main()
