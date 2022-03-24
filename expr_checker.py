#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
from inspect import getsource
from textwrap import dedent


def ast_default_check_type(method, value):
    safe_type = (str, int, type(None), type(range(0)))

    if type(value) not in safe_type and not (hasattr(value, "__self__") and type(value.__self__) in safe_type):
        raise ValueError(f"safe_eval didn't like {value}")

    return value


def ast_default_test(func, check_type, *args, **kwargs):
    for arg in args:
        check_type("arguments", arg)

    for arg in kwargs.values():
        check_type("arguments", arg)

    if func.__name__ == "<lambda>":
        return check_type("returned", func(*args))
    else:
        return check_type("returned", func(*args, **kwargs))


class NodeChecker(ast.NodeTransformer):
    def __init__(self, check_fn, allow_function_calls, check_type_fn, get_attr):
        self.check_fn = check_fn.__name__
        self.check_type_fn = check_type_fn.__name__
        self.fncall = allow_function_calls
        self.getattr = get_attr.__name__

        self.reserved_name = [self.check_fn, self.check_type_fn, self.getattr]

        super().__init__()

    def visit_Call(self, node):
        self.generic_visit(node)

        if not self.fncall:
            raise Exception("safe_eval didn't permit you to call any functions")

        if isinstance(node.func, ast.Attribute):
            return ast.Call(
                func=ast.Name(self.getattr, ast.Load()),
                args=[node.func.value, ast.Constant(node.func.attr), node],
                keywords=[]
            )

        else:
            self.generic_visit(node.func)

        return ast.Call(
            func=ast.Name(self.check_fn, ctx=ast.Load()),
            args=[node.func, ast.Name(
                self.check_type_fn, ctx=ast.Load())] + node.args,
            keywords=node.keywords
        )

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name in self.reserved_name:
            raise NameError(f"safe_eval: {node.name} is a reserved name")

        return node

    def visit_Attribute(self, node):
        self.generic_visit(node.value)

        if isinstance(node.ctx, ast.Load):
            subcall = ast.Call(
                func=ast.Name(self.getattr, ctx=ast.Load()),
                args=[node.value, ast.Constant(node.attr), node],
                keywords=[]
            )

            return ast.Call(
                func=ast.Name(self.check_type_fn, ctx=ast.Load()),
                args=[ast.Constant("attribute"), subcall],
                keywords=[]
            )

        elif isinstance(node.ctx, ast.Store):
            raise ValueError("safe_eval: doesn't permit you to store values in attributes")

        elif isinstance(node.ctx, ast.Del):
            raise ValueError("safe_eval: doesn't permit you to delete attributes")

    def visit_Assign(self, node):
        self.generic_visit(node.value)

        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id in self.reserved_name:
                    raise NameError(f"safe_eval: {target.id} is a reserved name")
            elif isinstance(target, ast.Attribute):
                raise ValueError("safe_eval: doesn't permit you to modify an attribute")  # FIXME with ast_set_attr
            elif isinstance(target, ast.Subscript) and isinstance(target.value,
                                                                  ast.Call) and target.value.func.id in ["globals",
                                                                                                         "locals"]:
                raise ValueError("safe_eval: doesn't permit you to modify locals() and globals()")
            else:
                raise NotImplementedError(f"{ast.dump(target, indent=4)}")

        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Name(self.check_type_fn, ctx=ast.Load()),
            args=[ast.Constant("constant"), node],
            keywords=[]
        )



def expr_checker(expr, get_attr, allow_function_calls=True, check_type=ast_default_check_type,
                 check_function=ast_default_test):
    code = f"""{dedent(getsource(check_type))}
{dedent(getsource(check_function))}
{ast.unparse(NodeChecker(check_function, allow_function_calls, check_type, get_attr).visit(ast.parse(expr)))}
    """
    return code
