#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
from copy import copy


_safe_type = None
_readonly = None


def check_type(obj):
    if type(obj) in {list, tuple, set}:
        list(map(check_type, obj))
        return obj
    elif type(obj) not in _safe_type:
        raise ValueError(f"safe_eval didn't like {obj}")
    else:
        return obj


def test(func, *args, **kwargs):
    list(map(check_type, kwargs.values()))
    list(map(check_type, args))

    return check_type(func(*args, **kwargs))


def check_ro(obj):
    if type(obj) in _readonly:
        return copy(obj)
    else:
        return obj


class NodeChecker(ast.NodeTransformer):
    def __init__(self, check_fn, allowed_attr):
        self.check_fn = check_fn.__name__
        self.allowed_attr = allowed_attr

        super().__init__()

    def visit_Call(self, node):
        list(map(self.visit, node.args))

        if isinstance(node.func, ast.Attribute):
            if node.func.attr not in self.allowed_attr:
                raise ValueError(
                    f"safe_eval doesn't allow you to read {node.func.attr}")

            name = copy(node.func.value)
            node.func.value.__class__ = ast.Call
            node.func.value.func = ast.Name("check_ro", ctx=ast.Load())
            node.func.value.args = [name]
            node.func.value.keywords = []
        
        else:
            self.generic_visit(node.func)            
            
        return ast.Call(
            func=ast.Name(self.check_fn, ctx=ast.Load()),
            args=[node.func] + node.args,
            keywords=node.keywords
        )

    def visit_FunctionDef(self, node):
        if node.name in [self.check_fn, "check_ro", "check_type"]:
            raise NameError(f"safe_eval: {node.name} is a reserved name")
        
        return node

    def visit_Name(self, node):
        if node.id in [self.check_fn, "check_ro", "check_type"]:
            raise NameError(f"safe_eval: {node.id} is a reserved name")

        return node

    def visit_Attribute(self, node):
        if node.attr not in self.allowed_attr:
            raise ValueError(
                f"safe_eval doesn't allow you to read {node.attr}")

        if isinstance(node.ctx, ast.Load):
            return ast.Call(
                func=ast.Name("check_type", ctx=ast.Load()),
                args=[node],
                keywords=[]
            )

        else:
            return ast.Call(
                func=ast.Name("check_ro", ctx=ast.Load()),
                args=[node.value],
                keywords=[]
            )

    def visit_Assign(self, node):
        list(map(self.visit, node.targets))
        return ast.Call(
            func=ast.Name("check_type", ctx=ast.Load()),
            args=[node.value],
            keywords=[]
        )


def expr_checker(expr, whitelist, allowed_attr, readonly, check_function=test):
    global _safe_type
    global _readonly

    _safe_type = whitelist
    _readonly = readonly

    return ast.unparse(NodeChecker(check_function, allowed_attr).visit(ast.parse(expr)))

