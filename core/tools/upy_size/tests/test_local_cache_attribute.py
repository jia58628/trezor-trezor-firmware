from ..src.upy_size.strategies.local_cache_attribute import local_cache_attribute

CODE = """\
def abc(msg):
    return msg.tre


def my_func(ctx, msg):
    # comment not to take msg.abc
    assert msg.abc is not None
    abc(msg.abc)
    x = msg.abc.xyz
    return MyMessage(abc=msg.abc)


def mutating_func(ctx, msg):
    assert msg.abc is not None
    msg.abc = 1
    abc(msg.abc)
    x = msg.abc.xyz
    return MyMessage(abc=msg.abc)
"""


def test_local_cache_attribute():
    res = local_cache_attribute(CODE, threshold=3)
    assert len(res) == 2

    assert res[0].func.name == "my_func"
    assert res[0].cache_candidate.cache_string == "msg.abc"
    assert res[0].cache_candidate.amount == 4
    assert res[0].gets_mutated is False
    assert res[0].saved_bytes() == 8

    assert res[1].func.name == "mutating_func"
    assert res[1].cache_candidate.cache_string == "msg.abc"
    assert res[1].cache_candidate.amount == 5
    assert res[1].gets_mutated is True
    assert res[1].saved_bytes() == 10
