#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import types
from inspect import getsource
from textwrap import dedent


def __ast_default_check_type(method, value):
    safe_type = (
        str, bytes, float, complex, int, bool, types.NoneType,
        tuple, list, set, dict,
        range,
        types.FunctionType, types.LambdaType, types.GeneratorType, types.MethodType,
        types.BuiltinFunctionType, types.BuiltinMethodType, types.WrapperDescriptorType,
        types.MethodWrapperType, types.MethodDescriptorType, types.ClassMethodDescriptorType,
    )

    if type(value) not in safe_type:
        raise ValueError(f"safe_eval didn't like {value}")

    return value


def __ast_default_check_call(func, check_type, *args, **kwargs):
    for arg in args:
        check_type("arguments", arg)

    for arg in kwargs.values():
        check_type("arguments", arg)

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
        node = self.generic_visit(node)

        if not self.fncall:
            raise Exception("safe_eval didn't permit you to call any functions")

        if isinstance(node.func, ast.Attribute):
            return ast.Call(
                func=ast.Name(self.getattr, ast.Load()),
                args=[node.func.value, ast.Constant(node.func.attr), node],
                keywords=[]
            )

        return ast.Call(
            func=ast.Name(self.check_fn, ctx=ast.Load()),
            args=[node.func, ast.Name(
                self.check_type_fn, ctx=ast.Load())] + node.args,
            keywords=node.keywords
        )

    def visit_Attribute(self, node):
        node = self.generic_visit(node)

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

    def visit_Subscript(self, node):
        node = self.generic_visit(node)
        return ast.Call(
            func=ast.Name(self.check_type_fn, ctx=ast.Load()),
            args=[ast.Constant("constant"), node],
            keywords=[]
        )


def expr_checker(expr, get_attr, allow_function_calls=True, check_type=__ast_default_check_type,
                 check_function=__ast_default_check_call, return_code=True):

    node_checker = NodeChecker(check_function, allow_function_calls, check_type, get_attr)
    user_code = ast.unparse(node_checker.visit(ast.parse(expr)))

    if return_code:
        code = '\n'.join([
            dedent(getsource(check_type)),
            dedent(getsource(check_function)),
            user_code
        ])
    else:
        code = user_code

    return (code, {check_type.__name__: check_type,
                   check_function.__name__: check_function,
                   get_attr.__name__: get_attr})
