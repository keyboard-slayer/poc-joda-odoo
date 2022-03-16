#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
from collections.abc import Iterable
from copy import copy


_safe_type = None
_allowed_attr = None
_readonly = None
_debug = False
_check_function = None


def check_type(obj):
    if obj in {list, tuple, set}:
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


def check_node(node):
    if isinstance(node, ast.Call):
        list(map(check_node, node.args))

        if isinstance(node.func, ast.Attribute):
            if node.func.attr in _allowed_attr:
                raise ValueError(
                    f"safe_eval doesn't allow you to read {node.attr}")

            name = copy(node.func.value)
            node.func.value.__class__ = ast.Call
            node.func.value.func = ast.Name("check_ro", ctx=ast.Load())
            node.func.value.args = [name]
            node.func.value.keywords = []
        else:
            check_node(node.func)

        func = node.func
        new_func = ast.Name(_check_function.__name__, ctx=ast.Load())
        node.args = [func] + node.args
        node.func = new_func
    elif isinstance(node, ast.Attribute):
        if node.attr not in _allowed_attr:
            raise ValueError(
                f"safe_eval doesn't allow you to read {node.attr}")

        if isinstance(node.ctx, ast.Load):
            attr = copy(node)
            node.__class__ = ast.Call
            node.func = ast.Name("check_type", ctx=ast.Load())
            node.args = [attr]
            node.keywords = []
        else:
            name = copy(node.value)
            node.value.__class__ = ast.Call
            node.value.func = ast.Name("check_ro", ctx=ast.Load())
            node.value.args = [name]
            node.value.keywords = []
    elif isinstance(node, ast.Assign):
        list(map(check_node, node.targets))

        value = copy(node.value)
        node.value.__class__ = ast.Call
        node.value.func = ast.Name("check_type", ctx=ast.Load())
        node.value.args = [value]
        node.value.keywords = []

    elif hasattr(node, "__dict__"):
        for attr in node.__dict__:
            assert(hasattr(node, "__dict__"))
            if hasattr(node.__dict__[attr], "__module__") and node.__dict__[attr].__module__ == "ast":
                check_node(node.__dict__[attr])
            elif isinstance(node.__dict__[attr], Iterable) and not isinstance(node.__dict__[attr], str):
                for subnode in node.__dict__[attr]:
                    if hasattr(subnode, "__module__") and subnode.__module__ == "ast":
                        check_node(subnode)
    else:
        raise NotImplementedError()


def expr_checker(expr, whitelist, allowed_attr, readonly, debug=False, check_function=test):
    global _safe_type
    global _allowed_attr
    global _readonly
    global _debug
    global _check_function

    _safe_type = whitelist
    _allowed_attr = allowed_attr
    _readonly = readonly
    _debug = debug
    _check_function = check_function

    expr_ast = ast.parse(expr)

    if _debug:
        print(ast.dump(expr_ast, indent=4))

    for node in expr_ast.body:
        check_node(node)
    
    if _debug:
        print(ast.unparse(expr_ast))

    return ast.unparse(expr_ast)
