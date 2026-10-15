# R194 — original v309 Linux identifier Java class and six-source compiler frontier

Client-side original JVM Java source reconstruction, stacked on R193 [PR #1087](https://github.com/Trexzo/SpawnPK-Client/pull/1087), tracked under [milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). This is **actual method-level original Java recovery**, not a fake compiler declaration.

## Original SHA-pinned source and bytecode evidence

The exact original full v309 client JAR SHA256:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Original **rs/secure/a.class** SHA256:
`9f85f7ff35546207eeb25433a26ab528a25f1fe999809375d6be77ad051aef3f`.

Reconstructed original-named **rs/secure/a.java** source-only, full six-method class:

| Original JVM method | Decompiled Java functionality | Acceptance |
| --- | --- | --- |
| `<init>()V` | original constructor | exact JVM Code |
| `a():String` | serial discovery fallback | exact JVM Code |
| `a(String):BufferedReader` | system command stream wrapper | exact JVM Code |
| `b():void` | `dmidecode -t system` search for `Serial Number:` | exact JVM Code |
| `c():void` | `lshal` fallback and hardware-serial regex cleanup | exact JVM Code |
| `<clinit>()V` | initialize static string cache | exact JVM Code |

**All six original methods, all 165 decoded JVM instructions** recompiled independently using JDK21 `javac --release 9 -g:none -proc:none -implicit:none` with EMPTY external and original .class classpath/sourcepath. A local `javap -p -c -v` comparison verifies original symbolic field/method operations, byte offsets, 25 StackMap frame entries, original exception handlers and access flags, with no changed control-flow paths. This is the complete Java source behavior as encoded in the original owner. No shell tool (`lshal`, `dmidecode`), recovered class or game process was ever executed.

Private one-source ZIP SHA256:
**46a23049635bd8b2ab24365847ea2ade195128aa8025508f0452fde14b77462b**.

Private Java source text SHA256:
**7bb4bbba8b89d3d2dda3330b317c954f6d165338920db1d90288d71944f35465**.

The source body is privately retained and is not published as original-derived proprietary Java.

## Integrated real source-only proof

An independently tested Java9 source set now consists of SIX original-evidenced semantic Java owners:
`rs/q/a` (ISAAC), `rs/v/a` (Signlink), `rs/v/a$a` (direction enum), `rs/k/j` (platform enum), `rs/secure/b` (macOS serial), and **`rs/secure/a`** (Linux serial). They compile in one source-only JDK build against THREE remaining explicitly non-original declaration-only helpers (`rs/f/a`, `rs/w/c`, `rs/secure/c`). The original outer Signlink still matches **24/24 complete method semantics**, 870 JVM decoded instructions modulo 35 previously documented `ldc` to `ldc_w` constant-index-width changes.

**No fake helper declarations are in the experimental full client source-tree overlay.**

## Actual full-source compiler measurements

The exact previous private R193 five-owner original Java experimental ZIP SHA256:
`7ec20525e1e2a51c78199102b46c54bd5b2ae9c0a9cd40783473d21a975e9eab`.

The new privately retained R194 six-owner experimental ZIP SHA256:
**dc5a23e63c03506093b21ffc4ab013a14fcbd21f70c847c688c9441b2b8d1b65**.

All **1,283** previous Java file bytes preserved, plus exactly one new original `rs/secure/a.java` (1,284 total). JDK21.0.12.1 with identical JDK-only compiler flags: `-J-Xmx4g --release 9 -g:none -proc:none -implicit:none -Xmaxerrs 10000 -classpath EMPTY -sourcepath EMPTY`.

| Private source compilation | Java files | Actual javac errors | Build |
| --- | ---: | ---: | --- |
| R193 prior overlay | 1,283 | **2,345** | Failed |
| R194 recovered Linux Java | **1,284** | **2,344** | Failed |
| Change | +1 | **−1** | Still fails |

R194 Javac stderr SHA256:
`80a5774d8866e1f37956644e38cc8194e12e9f210c2508de11be2f2a5c75e6d9`.

Error counts are measured from complete stderr and not extrapolated from capped compiler output. The result **does not** prove an independently buildable original client; it proves one additional recovered dependency reduces the controlled compiler frontier by one.

## Public GitHub verifier and scope

GitHub R194 tool reuses R193 SHA-pinned full-owner source-only Java9 verifier with pinned original `rs/secure/a.class`, 6 methods, 165 instructions, single original field ABI. A second method creates the exact private 1,284-source overlay, checks every previous source byte and validates a two-run complete Javac error delta. Ubuntu and Windows CI use unrelated invented Java9 classes with six method identities and IO/try/finally structures, plus negative mutations/incorrect digests; never original game code or system command execution.

**Remaining client-side dependencies:** original `rs/secure/c` (Windows install identifier), `rs/f/a` (large configuration owner), `rs/w/c` (MIDI audio). The v309 client also has hundreds of unrelated unresolved source/library dependencies and still reports 2,344 compiler errors. Full original source closure, original Java enum binary-identity/StackMap verification, production runtime/network/audio, private exact-input replay on GitHub, and derived-source redistribution authorization remain unverified. Keep DRAFT.

Next recover actual original Windows identifier source `rs/secure/c`, not another declaration-only stub; investigate `rs/w/c` original sound class and `rs/f/a` config with their own original JVM Code proofs.
