# Debugging T1 signatures

1. T1 firmware must be built with `DEBUG_T1_SIGNATURES=1` to be able to debug them
1. Load signing device or emulator (must have `PYOPT=0` for core or `DEBUG_LINK=1` 
   for T1 legacy) with:
   `trezorctl device load -m "table table table table table table table table table table table advance"` 
1. **Check FW header hash, not whole FW hash in the one output by cibuild**, by either trying to 
   install it on T1, or `head -c 1024 firmware/trezor.bin | sha256sum`
1. The sha256sum way will **work only before you sign the firmware first time**,
   better check by installing it or using scripts
1. Let's say your header hash is `9e82a06e05a73b6fc5236508c3d1f3cdd15868523191783cfa2bda78d6e349c6`
   for example.
1. Run the emulator or device (make sure not to confuse which are you using for signing)
1. Run `firmware_hash_sign_trezor.py 9e82a06e05a73b6fc5236508c3d1f3cdd15868523191783cfa2bda78d6e349c6`
1. Accept 5 signature requests on signing device
1. This will give you a list of 5 signatures for 5 keys
1. Copy three of the signatures and their indices into `trezor.bin.signatures` file, e.g.

```
1 bc8ed893fedc088ea4b45f775ea62ef84d8113a6c0f2d88d0fb6b8f4c26549eb02e88dffa3c06517729ce5b41da3678d88ac4a7ce3b0ad05a1ee0507f7165dd3
2 58f89a229b1d47011bd7771395c20bdce461bde2f150331e26a4cfc58456bdb0456e886f1d558b47f80982ec80dff941028fb4b1ef05e79fa32b6298dbf0bc5f
4 2a5ca0d3f7cad6b440a417779942158d70442e2ccd48875131d83a1644ae00022c531590a605d2ad415d778afda8b8118b47e4c47442014be64e90fa09b3a4ab
```

Finally use this file to patch signatures into the unsigned `trezor.bin`:

    fill_t1_fw_signatures.py firmware/trezor.bin trezor.bin.signatures

Example output for this hash:

```
Loaded FW image with header hash 9e82a06e05a73b6fc5236508c3d1f3cdd15868523191783cfa2bda78d6e349c6
Parsing sig line 1 - 1 bc8ed893fedc088ea4b45f775ea62ef84d8113a6c0f2d88d0fb6b8f4c26549eb02e88dffa3c06517729ce5b41da3678d88ac4a7ce3b0ad05a1ee0507f7165dd3

Parsing sig line 2 - 2 58f89a229b1d47011bd7771395c20bdce461bde2f150331e26a4cfc58456bdb0456e886f1d558b47f80982ec80dff941028fb4b1ef05e79fa32b6298dbf0bc5f

Parsing sig line 3 - 4 2a5ca0d3f7cad6b440a417779942158d70442e2ccd48875131d83a1644ae00022c531590a605d2ad415d778afda8b8118b47e4c47442014be64e90fa09b3a4ab

Patching sigindex 1 at offset 736
Patching signature bc8ed893fedc088ea4b45f775ea62ef84d8113a6c0f2d88d0fb6b8f4c26549eb02e88dffa3c06517729ce5b41da3678d88ac4a7ce3b0ad05a1ee0507f7165dd3 at offset 544
Patching sigindex 2 at offset 737
Patching signature 58f89a229b1d47011bd7771395c20bdce461bde2f150331e26a4cfc58456bdb0456e886f1d558b47f80982ec80dff941028fb4b1ef05e79fa32b6298dbf0bc5f at offset 608
Patching sigindex 4 at offset 738
Patching signature 2a5ca0d3f7cad6b440a417779942158d70442e2ccd48875131d83a1644ae00022c531590a605d2ad415d778afda8b8118b47e4c47442014be64e90fa09b3a4ab at offset 672
Writing output signed FW file firmware/trezor.bin.signed
```

It should show you the same header that you were signing and that shows on
the device. It will output `firmware/trezor.bin.signed`.

Update FW on T1 either via `trezorctl device firmware-update` or 
`make flash_firmware_jlink`.
