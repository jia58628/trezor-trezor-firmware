from ..src.upy_size.strategies import Settings
from ..src.upy_size.strategies.function_inline import function_inline

CODE = """\
def main(abc, xyz):
    x = 54
    func_used_also_elsewhere(x)
    return _square(x)

def _square(x):
    return x * x

def func_used_also_elsewhere(x):
    return x * x

class ABC:
    def __init__(self, x):
        __init__(self, x)
"""


def test_function_inline():
    SETTINGS = Settings(not_inlineable_funcs=["func_used_also_elsewhere"])

    res = function_inline(CODE, SETTINGS)
    assert len(res) == 1
    assert res[0].func.name == "_square"
    assert res[0].saved_bytes() == 50
