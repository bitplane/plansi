import operator


class Implied:
    def __new__(cls, default, specified=None):
        if specified is not None:
            return type(specified)(specified)
        return super().__new__(cls)

    def __init__(self, value, specified=None):
        self._value = value

    def __str__(self):
        return f"{str(self._value)} (implied)"

    def __repr__(self):
        return f"{repr(self._value)} (implied)"

    def __getattribute__(self, name):
        if name in {"_value", "__class__", "__dict__", "__str__", "__repr__"}:
            return super().__getattribute__(name)
        return getattr(self._value, name)


def forward(name):
    func = _operator_map.get(name)
    if func is not None:

        def method(self, *args, **kwargs):
            return func(self._value, *args, **kwargs)

        return method
    else:

        def method(self, *args, **kwargs):
            return getattr(self._value, name)(*args, **kwargs)

        return method


# Mapping from dunder name to operator function
_operator_map = {
    "__bool__": operator.truth,
    "__len__": operator.length_hint,  # or len, but this handles fallbacks
    "__getitem__": operator.getitem,
    "__setitem__": operator.setitem,
    "__delitem__": operator.delitem,
    "__eq__": operator.eq,
    "__ne__": operator.ne,
    "__lt__": operator.lt,
    "__le__": operator.le,
    "__gt__": operator.gt,
    "__ge__": operator.ge,
    "__add__": operator.add,
    "__radd__": operator.add,  # operator doesn't distinguish r* funcs
    "__sub__": operator.sub,
    "__rsub__": operator.sub,
    "__mul__": operator.mul,
    "__rmul__": operator.mul,
    "__matmul__": operator.matmul,
    "__rmatmul__": operator.matmul,
    "__truediv__": operator.truediv,
    "__rtruediv__": operator.truediv,
    "__floordiv__": operator.floordiv,
    "__rfloordiv__": operator.floordiv,
    "__mod__": operator.mod,
    "__rmod__": operator.mod,
    "__pow__": operator.pow,
    "__rpow__": operator.pow,
    "__contains__": operator.contains,
}


for name in _operator_map:
    setattr(Implied, name, forward(name))


def implied(o):
    return isinstance(o, Implied)
