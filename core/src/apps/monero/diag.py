from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Failure


if __debug__:
    import gc
    import micropython
    import sys

    from trezor import log

    PREV_MEM = gc.mem_free()
    CUR_MES = 0

    def log_trace(x=None) -> None:
        log.debug(
            __name__,
            "Log trace %s, ... F: %s A: %s, S: %s",
            x,
            gc.mem_free(),
            gc.mem_alloc(),
            micropython.stack_use(),
        )

    def check_mem(x: str | int = "") -> None:
        global PREV_MEM, CUR_MES

        gc.collect()
        free = gc.mem_free()
        diff = PREV_MEM - free
        log.debug(
            __name__,
            f"======= {CUR_MES} {x} Diff: {diff} Free: {free} Allocated: {gc.mem_alloc()}",
        )
        micropython.mem_info()
        gc.collect()
        CUR_MES += 1
        PREV_MEM = free

    def retit(**kwargs) -> Failure:
        from trezor.messages import Failure

        return Failure(**kwargs)

    async def diag(ctx, msg, **kwargs) -> Failure:
        msg_ins = msg.ins  # local_cache_attribute
        mem_check = check_mem  # local_cache_global
        log_debug = log.debug  # local_cache_attribute

        log_debug(__name__, "----diagnostics")
        gc.collect()

        if msg_ins == 0:
            mem_check(0)
            return retit()

        elif msg_ins == 1:
            mem_check(1)
            micropython.mem_info(1)
            return retit()

        elif msg_ins == 2:
            log_debug(__name__, "_____________________________________________")
            log_debug(__name__, "_____________________________________________")
            log_debug(__name__, "_____________________________________________")
            return retit()

        elif msg_ins == 3:
            pass

        elif msg_ins == 4:
            total = 0
            monero = 0

            for k, v in sys.modules.items():
                log.info(__name__, "Mod[%s]: %s", k, v)
                total += 1
                if k.startswith("apps.monero"):
                    monero += 1
            log.info(__name__, "Total modules: %s, Monero modules: %s", total, monero)
            return retit()

        elif msg_ins in [5, 6, 7]:
            mem_check()
            from apps.monero.xmr import bulletproof as bp

            mem_check("BP Imported")
            from apps.monero.xmr import crypto

            mem_check("Crypto Imported")

            bpi = bp.BulletProofBuilder()
            bpi.gc_fnc = gc.collect
            bpi.gc_trace = log_trace

            vals = [crypto.Scalar((1 << 30) - 1 + 16), crypto.Scalar(22222)]
            masks = [crypto.random_scalar(), crypto.random_scalar()]
            mem_check("BP pre input")

            if msg_ins == 5:
                bp_res = bpi.prove_testnet(vals[0], masks[0])
                mem_check("BP post prove")
                bpi.verify_testnet(bp_res)
                mem_check("BP post verify")

            elif msg_ins == 6:
                bp_res = bpi.prove(vals[0], masks[0])
                mem_check("BP post prove")
                bpi.verify(bp_res)
                mem_check("BP post verify")

            elif msg_ins == 7:
                bp_res = bpi.prove_batch(vals, masks)
                mem_check("BP post prove")
                bpi.verify(bp_res)
                mem_check("BP post verify")

            return retit()

        return retit()
