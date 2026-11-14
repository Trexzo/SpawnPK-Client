# R387 — original-v309 resource preservation audit (owner-private, read-only)

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R386 draft PR #1181.
**KEEP DRAFT / UNMERGED; Source-M1 private-source release gate CLOSED.**

## Genuine Windows evidence

The unchanged owner-controlled original v309 archive is SHA-256
ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
(17,532,075 bytes). The separate resource-only companion is SHA-256
9a6a23750bedd39f49563c54bbbf89a0214f40e7f8fd8e0b1c08ba3da863fde4
(5,812,724 bytes).

A fresh read-only Windows replay on the authorized owner PC reported:
- Original ZIP: **10,921 entries**: 10,502 class files and 419 resources.
- Companion ZIP: **419 resource entries, zero class files**.
- **419/419 original resource names and decompressed SHA-256 hashes matched**.
- Both whole-file SHA-256 values were independently rechecked on the PC.

The project now includes a repeatable, bounded, read-only Python verifier for
these two **explicit local** inputs. It checks SHA-pins, unique/normalized ZIP
members, size limits, counts, exact resource paths and each resource's bytes.
It opens no original class payload, extracts nothing, performs no classloading
or network operation, and changes no file. Output is aggregate-only (no source
member names, private paths or original resource bytes).

Run from a trusted isolated project checkout, supplying the local original and
resource companion paths:

    python tools/r387/verify_original_resources.py --original PATH_TO_V309_ORIGINAL.jar --companion PATH_TO_RESOURCES_ONLY.jar

### R387 verified Windows replay after portability correction

The GitHub-committed verifier itself was downloaded at pinned commit
af6d9f2bc99e5968fc953059323f475b746c4798 and executed against the
two SHA-pinned owner-private archives on the Windows PC:
**R387_RESOURCE_PRESERVATION_PASS, 419/419 resources**. Its 17 synthetic
negative/positive tests also passed **17/17 on Windows Python 3.12**.
An initial synthetic backslash-fixture failure exposed Windows' zipfile
filename normalization. The verifier now checks ZipInfo.orig_filename
against the normalized filename, and the test mutates actual ZIP header
filename bytes to cover the unsafe raw spelling cross-platform. No
staging or live-client files were modified. Hosted public CI remains
separate from this owner-private Windows evidence.

## Limits and blocked gates

The reconstructed R381/R386 candidate is 1,388 compiled classes with no
non-class resources; it does not itself contain the 419 original resources.
The class-only filtered dependency archives likewise lack resources and have
9,326 overlapping class entry paths. Neither loading both dependencies nor
adding the resource companion to a runtime classpath is yet approved.

**Resource preservation is NOT original bytecode parity or runtime parity.**
No valid original-v309 class remapping, classloader initialization, game startup,
GUI/login/reconnect, v312 compatibility, or user-cache safety has been proven.
R386's *full* 1,277-source Windows compilation is still untested because its
owner-private one-layer ZIP is not present on that PC. Fixture-only Windows
tests and Linux recompilation do not fulfill this gate.

## Public GitHub scope

Four public-safe files: this report, generic verifier, 17 small synthetic
regression tests and cross-platform Windows/Ubuntu CI workflow. **No** original
v309 binary, recovered Java, compiled candidate, dependency JAR, resource
companion archive, game cache, credential or local path is committed. Hosted
CI runs synthetic fixtures only and does not prove real private client behavior.
No staging-file cleanup, original JAR mutation, v312 live modification or
release-gate change is authorized.
