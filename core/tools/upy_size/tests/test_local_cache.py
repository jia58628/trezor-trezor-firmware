from ..src.upy_size.strategies.local_cache import local_cache

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


def test_local_cache():
    res = local_cache(CODE, low_threshold=3)
    assert len(res) == 2

    assert res[0].func.name == "my_func"
    assert res[0].cache_candidate.cache_string == "msg.abc"
    assert res[0].cache_candidate.amount == 4
    assert res[0].gets_mutated == False
    assert res[0].saved_bytes() == 8

    assert res[1].func.name == "mutating_func"
    assert res[1].cache_candidate.cache_string == "msg.abc"
    assert res[1].cache_candidate.amount == 5
    assert res[1].gets_mutated == True
    assert res[1].saved_bytes() == 10
