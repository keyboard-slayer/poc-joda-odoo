#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
from copy import copy
from enum import auto, Enum
from inspect import getsource
from textwrap import dedent

_readonly = None


def ast_default_check_type(method, value):
    safe_type = (str, int, type(None), type(range(0)))

    if isinstance(value, (list, tuple, set)):
        for val in value:
            ast_default_check_type(method, val)
        return value
    elif type(value) not in safe_type:
        raise ValueError(f"safe_eval didn't like {value}")
    
    return value


def ast_default_test(func, check_type, *args, **kwargs):
    for arg in args:
        check_type("arguments", arg)
    
    for arg in kwargs.values():
        check_type("arguments", arg)

    return check_type("returned", func(*args, **kwargs))


def ast_check_ro(obj):
    if type(obj) in _readonly:
        return copy(obj)
    else:
        return obj


class NodeChecker(ast.NodeTransformer):
    def __init__(self, check_fn, allow_function_calls, check_type_fn, allowed_attr):
        self.check_fn = check_fn.__name__
        self.check_type_fn = check_type_fn.__name__
        self.allowed_attr = allowed_attr
        self.fncall = allow_function_calls

        self.reserved_name = [self.check_fn, self.check_type_fn, "ast_check_ro"]

        super().__init__()

    def visit_Call(self, node):
        list(map(self.visit, node.args))

        if not self.fncall:
            raise Exception("safe_eval didn't allow you to call any functions")

        if isinstance(node.func, ast.Attribute):
            if node.func.attr not in self.allowed_attr:
                raise ValueError(
                    f"safe_eval doesn't allow you to read {node.func.attr}")

            name = copy(node.func.value)
            node.func.value.__class__ = ast.Call
            node.func.value.func = ast.Name("ast_check_ro", ctx=ast.Load())
            node.func.value.args = [name]
            node.func.value.keywords = []

        else:
            self.generic_visit(node.func)

        return ast.Call(
            func=ast.Name(self.check_fn, ctx=ast.Load()),
            args=[node.func, ast.Name(
                self.check_type_fn, ctx=ast.Load())] + node.args,
            keywords=node.keywords
        )

    def visit_FunctionDef(self, node):
        if node.name in self.reserved_name:
            raise NameError(f"safe_eval: {node.name} is a reserved name")

        return node

    def visit_Name(self, node):
        if node.id in self.reserved_name:
            raise NameError(f"safe_eval: {node.id} is a reserved name")

        return node

    def visit_Attribute(self, node):
        if node.attr not in self.allowed_attr:
            raise ValueError(
                f"safe_eval doesn't allow you to read {node.attr}")

        if isinstance(node.ctx, ast.Load):
            return ast.Call(
                func=ast.Name(self.check_type_fn, ctx=ast.Load()),
                args=[ast.Constant("attribute"), node],
                keywords=[]
            )

        elif isinstance(node.ctx, ast.Store):
            return ast.Call(
                func=ast.Name("ast_check_ro", ctx=ast.Load()),
                args=[node.value],
                keywords=[]
            )

        elif isinstance(node.ctx, ast.Del):
            raise ValueError("safe_eval: You can't delete attribute")

    def visit_Assign(self, node):
        node = self.generic_visit(node)

        return ast.Call(
            func=ast.Name(self.check_type_fn, ctx=ast.Load()),
            args=[ast.Constant("assignation"), node.value],
            keywords=[]
        )


def expr_checker(expr, allowed_attr, readonly, allow_function_calls=True, check_type=ast_default_check_type, check_function=ast_default_test):
    global _readonly

    _readonly = readonly
    
    code = f"""{dedent(getsource(check_type))}
{dedent(getsource(check_function))}
{ast.unparse(NodeChecker(check_function, allow_function_calls, check_type, allowed_attr).visit(ast.parse(expr)))}
    """
    return code
