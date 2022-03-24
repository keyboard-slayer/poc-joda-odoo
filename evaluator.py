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
    if key not in ("a", "x", "tell_me_hi", "set_x_value"):
        raise ValueError(f"safe_eval doesn't permit you to read {key}")

    return value


def safe_eval(code):
    _globals = {'__builtins__': _BUILTINS}
    patch_code, _locals = expr_checker(code, safe_get_attr, return_code=False)

    return unsafe_eval(patch_code, _globals, _locals)


def safe_eval_no_calls(code):
    _globals = {'__builtins__': _BUILTINS}
    patch_code, _locals = expr_checker(code, safe_get_attr, return_code=False, allow_function_calls=False)

    return unsafe_eval(patch_code, _globals, _locals)

# NOTE: Only for testing purpose
def safe_eval_test(code, scope, check_type=None):
    _globals = {'__builtins__': _BUILTINS}

    if check_type is None:
        patch_code, _locals = expr_checker(code, safe_get_attr, return_code=False)
    else:
        patch_code, _locals = expr_checker(code, safe_get_attr, return_code=False, check_type=check_type)

    _locals.update(scope)

    return unsafe_eval(patch_code, _globals, _locals)
