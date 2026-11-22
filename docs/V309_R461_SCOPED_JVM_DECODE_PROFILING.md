# R461 — Profile and bound repeated JVM instruction decoding inside consolidated R459

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R460 draft PR #1257, Windows/Ubuntu Python 3.11/3.13 4/4 tests and Recovery CI passed on `573fcc51`.  
**State:** DRAFT / UNMERGED / NOT DEPLOYED.

## Problem and conservative change

R459 solved *repeated classfile disk reads*, but source inspection of its Code path confirms that even the **same immutable method bytecode** is decoded repeatedly by the R458 bootstrap/condy scan, R450 resource proximity, R451 straight-line, R452 forward CFG and R456 typed member opcode scanner. Each uses R450's authoritative `instructions(code)` boundary decoder. R460 measured a large reduction in file reads on fabricated two-class input but did not prove remaining parse CPU overhead.

R461 makes **one targeted bounded optimization**:
- R450 retains its original `_instructions_uncached(code)` decoder unchanged, including all existing bounds, `wide`, switch alignment and malformed-opcode refusals. For default R450–R458 callers, the public `instructions(code)` entrypoint still invokes that exact parser without caching.
- R450 adds a `scoped_instruction_cache` audit decorator using Python `ContextVar`, not shared global mutable decoder state. **Only R459.inspect** is decorated. It creates a fresh local cache at inspection start, resets it even on exception, and refuses nested scopes. Both owner current-state R446 inventory scans and all source/dependency SHA gates stay untouched.
- The cache keys **immutable method Code bytes** and stores immutable decoded instruction triples; each cached return is a **fresh list** so a caller cannot modify another parser's state. Strict syntax checking happens on the first cache miss and is never bypassed for a malformed input. Bounded LRU limits: **64 method bodies**, **256 KiB raw code bytes**, **32,768 decoded instructions**, **16 KiB per cacheable method** and **4,096 decoded instructions per cacheable method**. Larger methods still go through the original decoder with no caching. Evictions do not relax safety limits or create speculative results.
- The decorated R459 output adds only deterministic **aggregate** decoder cache hits/misses, evictions, current cache entries and oversized-body skips. No code bytes, source method signatures, filesystem paths, cache keys or private hashes go to stdout. Caches are never written to disk, shared between threads or retained between audits.

The R459 coordinator still rereads every class in both independent full R446 SHA inventory scans and once for evidence, reopens exact pinned original v309 JAR and both dependencies under prior limits, preserves complete source/class/dependency SHA reconciliation, and retains all independent R453–R458 structural evidence/cross-checks. Reusing *bytecode instruction boundaries* does not replace repeated member/class CP parsing, JVM stack verification or full runtime linking.

## Measurable profiling and evaluation

`tools/r461/profile_scoped_decoder.py` uses `cProfile` to run both **R459.inspect's original undecorated implementation** and its new scoped-cache wrapper over identical SHA-pinned inputs, then compares shared public evidence counts and **exact private worklists in RAM**. These private objects are not emitted. It uses only an **allowlist of public repository Python filenames and function symbols** to report the twelve hottest public functions by instrumented Python self time. Absolute paths, private source class names and private bytecode are redacted by construction.

`cProfile` timing is instrumentation-distorted and **must not be treated as a real audit speedup**. The independently measured R460 benchmark remains the source for synthetic wall-clock and bounded file-read comparisons; R461 CI also reruns its synthetic timing runner after the cache is enabled, without asserting a minimum speed ratio or improvement.

Synthetic profiling:
```powershell
python -B tools\r461\profile_scoped_decoder.py --synthetic
```

Authorized owner-only read-only profiler (when the PC and exact pinned original are actually accessible):
```powershell
python -B tools\r461\profile_scoped_decoder.py --owner-original-v309-jar '<owner-local exact original v309 client.jar>'
```

No public/private report file is saved, no Java, game client, DLL or user history is executed/read, no new JAR assembled, and no persistent cache is introduced.

## Verification and remaining gaps

**27 new invented regression cases** cover unchanged legacy code semantics, fresh-list isolation, LRU eviction, strict byte/instruction limits, uncached oversize path, malformed/truncated opcode refusal, cache reset on success/failure, nested-cache refusal, thread isolation, actual low-level decode-call reduction, exact SHA-gated R459 aggregate **and private worklist parity**, cProfile safe symbol allowlists, no private path leaks, source mutation and pinned original rejection, and CLI refusal. Cross-platform Windows/Ubuntu × Python 3.11/3.13 CI also reruns R460→R445, R442, R426 synthetic suites and labels synthetic benchmark numbers explicitly.

The authorized owner desktop `DESKTOP-LTXXO4K` remained **offline (last seen 170 hours ago)** at R461 intake. No original private v309/v312 Jar, actual 1,277 source/1,394 compiled owner file tree, real asset packaging, live JVM, login, interface rendering, gameplay FPS or real network latency is measured here. Missing **independently approved historical R421 inventory** cannot be fabricated by a current SHA scan. Synthetic tests prove audit design safeguards, **not** 100% original SpawnPK reconstruction or real runtime optimization.

**Keep draft/unmerged; no source or client replacement, player history access, LootTrackerPlugin writer enablement, R415/R417 deletion-intent journal cleanup, persistent write unlock, release or merged deployment is authorized.**
