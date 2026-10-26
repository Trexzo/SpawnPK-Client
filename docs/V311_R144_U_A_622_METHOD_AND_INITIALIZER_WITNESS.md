# SpawnPK original-v311 R144 — 622/870 source-recovered JVM instructions in rs/u/a

**Original-v311 evidence dated 2026-10-26.** Pinned owner JAR SHA-256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original `rs/u/a.class` SHA-256: `8e5de2d21852923e5837f5977f79e18c0033ffdf82d1fea4f5fb314bdaee461d`.

## R143 → R144: +67 genuine METHOD-only witnesses

| Newly source-recovered original member | Matched ordered original JVM instructions |
| --- | ---: |
| `public static boolean d()` | 7/7 |
| `public static String e()` | 17/17 |
| `public static void a(double)` | 5/5 |
| Original `static {}` / `<clinit>` | 38/38 |
| **New R144** | **67/67** |
| Reverified R143 existing methods | 555/555 |
| **Total R144 method witnesses** | **23 of 24 original method bodies / 622 of 870 instructions** |

Exact original symbolic JVM instructions and numeric byte offsets, descriptors, access flags, per-method stack/local/code sizes and exception-handler intervals all match for the 23 selected bodies. **17/17** original invokedynamic instruction sites match their corresponding original bootstrap arguments (**13 distinct recipes**). The original 248-instruction `run()` is **not** source-recovered and is excluded from all acceptance counts.

A single private `javac --release 9 -proc:none -g:none` compile uses one incomplete reconstructed Java source with **empty original game/vendor compiler classpath and sourcepath**. Nonoriginal nested compiler donor types are explicitly excluded. Copy-only constant-pool metadata restoration retargets seven source-level donor method/field references and one nested allocation class to original symbolic owners (`rs/k/j`, `rs/secure/a,b,c`, `rs/v/c`), preserving the R143 `rs/f/a.B` owner restoration and removal of two compiler-only checked Exceptions attributes. **25/25 compiled Code payloads are byte-identical before and after metadata-only restoration; no executable bytecode is patched.**

## Strict limits

The complete original class contains **34 fields / 24 methods**, while this incomplete research class has **30 fields / 25 method entries** including nonoriginal `run()` and compiler-only helper. It is **not a recovered full original class**, cannot be safely loaded into the client, and has not been initialized or executed. No network calls, sockets, hardware identification, OS/process commands, files, audio, threads or gameplay have been exercised.

**Independent clean ZIP replay:** source compile + direct original JAR comparison **622/622**, **23/23** original method declarations/exception/resources, **17/17** bootstrap sites, **25/25** unchanged Code attributes. **16/16** fail-closed private negative candidates passed, including actual source mutations with refreshed source and compiled-class hash pins as well as false ledger/full-class/runtime claims.

Owner-private archive (never upload to public GitHub): `SpawnPK-v311-R144-U-A-622-Instruction-Private-Research.zip`, **16,821 bytes, 9 entries, SHA-256 `30b330938700b728289946c35d0b5844b81fe2651a2b983bd30ae7242038109f`**. It contains reconstructed research source and private verifiers, not original/rebuilt game binaries, assets, credentials or real device identifiers.

The [public synthetic R144 Java9 tests](../tests/test_v311_synthetic_r144_method_frontier.py) are wholly original-independent; all **4/4 passed locally**. GitHub-hosted public CI cannot certify original game source or bytecode.

**Accepted distinct original source ledger stays 135/1,184 classes and 13,504 original matched instructions across separate source islands; R144 has ZERO new accepted full-class credit.** Largest single source-only integrated original build remains R136 **106 classes / 10,960 original instructions**.

**Next R145:** restore genuine `run()` (248 instructions) from Java9 source without running game or device/network/audio/file methods. Afterwards separately verify all original fields, methods, constructors, class attributes, dependencies and integrated compile before any whole-class promotion. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
