# R462 — bounded per-audit generic JVM Signature grammar memoization

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R461 draft PR #1258 at `9f0c7567`, 4/4 Windows/Ubuntu Python 3.11/3.13 CI passed.  
**State:** DRAFT, UNMERGED, owner-only static inspection; no installed client changes.

## Evidence-based motivation

R461's invented two-class `cProfile` trace shows that repeated JVM Code instruction decoding was safely reused (**12 hits, 3 misses**) while forward-branch resource analysis and parsing metadata remained visible Python CPU activity. The strict R450 generic JVM Signature parser also involves repeated Python character and recursive type grammar calls (431 `ch()` calls in the recorded synthetic trace). That does not demonstrate that actual owner classfiles repeat identical generic signatures, nor that this is the largest real-world performance issue.

R462 makes a **narrow opt-in optimization** with measurable correctness safeguards: cache only *validated* R450 generic Signature results when an identical `(signature text, signature kind)` occurs multiple times **within one SHA-gated R459 inspection**.

## Implementation

`tools/r450/classfile_signature_resource.py` preserves the legacy parser as `_generic_signature_refs_uncached(signature, kind)`, including the exact original nested generic class, method argument, throws and type-variable grammar constraints, depth and length budgets, and malformed input refusals. The public `generic_signature_refs` calls that unchanged parser by default; only R459's already established ContextVar-based inspection scope enables R462's new signature cache.

The signature cache:
- Keys on the *entire* immutable signature string and signature kind (`class`, `field`, or `method`), never on a hash alone.
- Stores immutable `frozenset` names; **returns a fresh mutable `set`** on cache hits so consumers cannot mutate cached results.
- Refuses incomplete, unsafe, malformed, non-ASCII, oversized or wrong-kind signatures using the original parser. Invalid strings are **never cached or converted to partial success**. Invalid/unhashable argument types are routed to the strict original parser before dictionary access.
- Has separate bounded LRU limits: **128 signatures**, **64 KiB combined signature text**, **2,048 total cached reference-name entries**, **8 KiB per cacheable signature** and **256 reference names per signature**. Entries are evicted on pressure and oversize valid signatures are analyzed normally without caching.
- Uses the R461 per-audit ContextVar scope with automatic cleanup on success or exception. No persistent cache, cross-audit sharing, unsafe global mutable reuse or disk writes. The existing decoded-instruction LRU remains independent, including its budgets.
- Adds **aggregate-only** R462 signature hit/miss, eviction, skip and entry count to R459's stdout. No owner method names, field signatures, private class or source path, signature strings, bytecode bytes or hash values are printed or uploaded.

R459's independent start/end R446 full source/class/dependency SHA observations, per-class evidence pass SHA, pinned original v309 JAR SHA, R239/R218 dependency ZIP admission, Store source/class fingerprint pins, complete inherited member and bootstrap checks, resource-site evidence, and owner-private double-scan custody are unchanged. It still refuses to create or approve the missing historical R421 full source/class inventory.

## Verification and reproducibility

`tests/test_v309_r462_scoped_signature_parsing.py` adds **25 invented tests**: legacy/direct parser equality, same-key reuse and signature-kind separation; malformed descriptor rejection; mutation-proof fresh sets; zero/low entry, character and reference budgets with LRU evictions; oversized uncached fallback; cross-scope and concurrent thread isolation; reduced uncached generic parser invocations; repeated signature attributes in an entirely invented Java11 class; exact R459 private-worklist and public aggregate parity against `inspect.__wrapped__`; current owner-fake SHA admissions, original pin mutation refusal, and no release/history claims.

Windows and Ubuntu Python 3.11/3.13 CI includes all R461–R445, R442/R426 fabricated regression suites and synthetic R461 cProfile. This proves consistency on invented inputs, **not** real R421 coverage or performance.

Existing synthetic profiler, when run after R462, may show no signature hits if its two-class fixture has no shared generic signatures. Therefore R462 makes **no numeric real owner, audit-wide or game-client speedup claim**; real R421 gains depend on repeated signature distributions and must be measured on the authorized owner machine when reachable. No automated change to the installed game, classloader, packet handling or FPS controls.

## Owner-only usage and limitations

The same R459 owner-only read-only CLI remains the entrypoint (once reachable):

```powershell
python -B tools\r459\audit_consolidated_inspection.py --original-v309-jar '<owner-local exact SHA-pinned original v309 JAR>'
```

The source inventory is expected to contain 1,277 isolated Java source files and 1,394 compiled Java11 classfiles, while the pinned original v309 archive contains 10,502 classes and 419 resources. These numbers are **inventory gates**, not proof of complete original source reconstruction, actual v312 runtime compatibility, compile/link success, required asset packaging, full GUI/login/gameplay or low-latency operation.

The user desktop `DESKTOP-LTXXO4K` was offline at R462 intake. Full independently approved historical R421 custody remains absent. No Java code execution, private source upload, production game history access, R415/R417 journal marker removal, write fence unlock, PR merge, release, or installed client replacement is authorized.

**Keep draft and unmerged.**
