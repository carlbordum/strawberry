import sys
from dataclasses import (  # type: ignore
    _FIELD,
    _FIELD_INITVAR,
    _FIELDS,
    _HAS_DEFAULT_FACTORY,
    _POST_INIT_NAME,
    MISSING,
    _create_fn,
    _field_init,
    _init_param,
    _set_new_attribute,
)


def dataclass_init_fn(fields, frozen, has_post_init, self_name, globals):
    """
    We create a custom __init__ function for the dataclasses that back
    Strawberry object types to only accept keyword arguments. This allows us to
    avoid the problem where a type cannot define a field with a default value
    before a field that doesn't have a default value.

    An example of the problem:
    https://stackoverflow.com/questions/51575931/class-inheritance-in-python-3-7-dataclasses

    Code is adapted from:
    https://github.com/python/cpython/blob/v3.9.6/Lib/dataclasses.py#L489-L536

    Note: in Python 3.10 and above we use the `kw_only` argument to achieve the
    same result.
    """
    # fields contains both real fields and InitVar pseudo-fields.

    locals = {f"_type_{f.name}": f.type for f in fields}
    locals.update(
        {
            "MISSING": MISSING,
            "_HAS_DEFAULT_FACTORY": _HAS_DEFAULT_FACTORY,
        }
    )

    body_lines = []
    for f in fields:
        line = _field_init(f, frozen, locals, self_name)
        # line is None means that this field doesn't require
        # initialization (it's a pseudo-field).  Just skip it.
        if line:
            body_lines.append(line)

    # Does this class have a post-init function?
    if has_post_init:
        params_str = ",".join(f.name for f in fields if f._field_type is _FIELD_INITVAR)
        body_lines.append(f"{self_name}.{_POST_INIT_NAME}({params_str})")

    # If no body lines, use 'pass'.
    if not body_lines:
        body_lines = ["pass"]

    _init_params = ["*"] + [_init_param(f) for f in fields if f.init]

    return _create_fn(
        "__init__",
        [self_name] + _init_params,
        body_lines,
        locals=locals,
        globals=globals,
        return_type=None,
    )


def add_custom_init_fn(cls):
    fields = [
        f
        for f in getattr(cls, _FIELDS).values()
        if f._field_type in (_FIELD, _FIELD_INITVAR)
    ]
    globals = sys.modules[cls.__module__].__dict__

    _set_new_attribute(
        cls,
        "__init__",
        dataclass_init_fn(
            fields=fields,
            frozen=False,
            has_post_init=hasattr(cls, _POST_INIT_NAME),
            self_name="__dataclass_self__" if "self" in fields else "self",
            globals=globals,
        ),
    )
