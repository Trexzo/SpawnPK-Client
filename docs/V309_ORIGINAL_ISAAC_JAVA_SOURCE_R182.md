# R182 — full original v309 ISAAC Java source recovery

Original-client milestone #1004, stacked on R181 #1072. This restores actual original JVM method behavior, not a declaration-only mapping.

## Exact private original-v309 evidence

- Original full JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Original rs/q/a.class SHA256: eea77b6d7a3a00c997acd46926005ef5e6fe93cd1d4f06668d62bdee85b3c7d0
- One original-name Java source privately rebuilt using javac --release 9 -g:none -proc:none -implicit:none, with no original or external classfile on compiler classpath.
- Four complete methods: <init>([I)V = 21/21 instructions; a()I = 19/19; b()V = 135/135; c()V = 627/627; **802/802 total**.
- Independent local javap -p -verbose comparison additionally verifies complete operation offsets, symbolic field/method references and operands, method descriptors/access modifiers, max stack/locals/args and StackMapTable presence. All six original field identities/access flags match.
- Original full classfile byte identity is NOT claimed.
- Private Java source text SHA256: f09961878757eb848c17efc7b950f8cf6393a5fc7935f7fba8b5a7b8d8f6437c
- Private original-name one-source ZIP SHA256: 09ad2bbf2a8fd83c26fb3a2c9c22de0a08ae77ab54ba5ad4c88f4d055f91d431

## Actual private tree and compiler experiment

Private baseline recovered-source/v309/src had 1,278 Java files (ZIP SHA256 dd68b18a4e60e7d9b2431811a1531f4e33bfa75ac1adb9a4f07100a64e99d6da). A private overlay added ONLY rs/q/a.java, preserved all previous 1,278 source bytes, and produced a 1,279-file source ZIP (SHA256 41162bc5d8e88a1ee455c8df54f3f5acba984e9de7d932f15dd6d19500d966f0).

A same-JDK21, same --release 9, identical empty original/external classpath and compile-option pair reported:

| Snapshot | JDK-only javac errors |
| --- | ---: |
| 1,278 files before original cipher | 2,339 |
| 1,279 files after original cipher | 2,339 |

**No compiler error reduction is claimed.** The whole original-v309 client remains uncompiled. These counts cannot be compared directly with R179's distinct 1,279-file Packet-overlay 2,343-error candidate; both new owners should be combined privately and measured together.

## Verification and boundaries

The new private-input R182 tool requires exact SHA pins, the full original 4-method/802-instruction class, six original field identities, class/super/major/access identity, and source-only Java9 compilation. It rejects unverified extra emitted .class files, incorrectly changed Java instructions and mutated original inputs. A separate guarded overlay preserves every baseline Java file, but does not itself prove source correctness. Hosted Ubuntu/Windows regression tests use unrelated synthetic Java9 sources and original-unrelated classfiles only.

The private original-derived Java and raw original binary are NOT committed to public GitHub. The original client's runtime, full-source build, external dependency closure and redistribution authorization remain unverified. Remaining four-helper track after this class: rs/v/a, rs/h (already under an independent R180 queue branch), and rs/f/a.
