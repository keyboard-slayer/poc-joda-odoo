from expr_checker import __ast_default_check_type, __ast_default_check_call, expr_checker

unsafe_eval = eval

_BUILTINS = {
    'True': True,
    'False': False,
    'None': None,
    'bytes': bytes,
    'str': str,
    'unicode': str,
    'bool': bool,
    'int': int,
    'float': float,
    'enumerate': enumerate,
    'dict': dict,
    'list': list,
    'tuple': tuple,
    'map': map,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'filter': filter,
    'sorted': sorted,
    'round': round,
    'len': len,
    'repr': repr,
    'set': set,
    'all': all,
    'any': any,
    'ord': ord,
    'chr': chr,
    'divmod': divmod,
    'isinstance': isinstance,
    'range': range,
    'xrange': range,
    'zip': zip,
    'Exception': Exception,
    'print': print,
    '__ast_default_check_type': __ast_default_check_type,
    '__ast_default_check_call': __ast_default_check_call
}


def safe_get_attr(obj, key, value):
    # NOTE: Those keys are for testing purpose
    if key not in ("a", "x", "tell_me_hi", "set_x_value", "say_something_else", "say_goodbye", "__str__", "__len__"):
        raise ValueError(f"safe_eval doesn't permit you to read {key}")

    return value


def safe_eval(expr, globals_dict={}, locals_dict={}, mode="eval", check_type=None, allow_functions_calls=True):
    if globals_dict is not None:
        globals_dict = dict(globals_dict)

    if locals_dict is not None:
        locals_dict = dict(locals_dict)

    globals_dict['__builtins__'] = _BUILTINS

    if check_type is None:
        code, scope = expr_checker(
            expr, safe_get_attr, allow_function_calls=allow_functions_calls, allow_private=True, return_code=False)
    else:
        code, scope = expr_checker(expr, safe_get_attr, check_type=check_type,
                                   allow_function_calls=allow_functions_calls, allow_private=True, return_code=False)

    globals_dict.update(scope)

    c = compile(code, "", mode)
    return unsafe_eval(c, globals_dict, locals_dict)
