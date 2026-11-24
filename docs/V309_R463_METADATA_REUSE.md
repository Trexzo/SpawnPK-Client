# R463 — witness-bound R456 classification reuse and descriptor-shape caching

Repository: Trexzo/SpawnPK-Client
Parent: R462 draft PR #1263 (`db968f0`)
Status: DRAFT / UNMERGED / SYNTHETIC CI ONLY

## Confirmed redundancy

The SHA-gated consolidated R459 path already runs R456.analyze on the decoded
member sites. The next R457.analyze call internally invokes the *same*
R456.analyze again on exactly those inputs, including redundant ancestry,
visibility and static/instance classification. Both are static checks, not
proof of JVM runtime linking.

R451 and R452 also each parse a method descriptor when tracing the same
resource-loading call; R457 separately reparses method descriptors for
repeated callsites. R451 and R457 have intentionally *different* descriptor
validation contracts and must not blindly share a cross-domain result.

## R463 implementation

1. `tools/r463/reuse_validated_metadata.py` introduces an ephemeral frozen
   `OpcodeWitness` that binds the selected safe R456 summary
   values to the EXACT in-memory rebuilt/selected/site collection objects and
   dynamic count already inspected by R456.
2. R457 has an optional `prior_witness` parameter; the default
   still runs R456 independently. The optimized path refuses mismatched
   identities, counts, types and forged method/field totals, but skips a
   second expensive ancestor/member-visibility classification.
3. `DescriptorShapes` is one transient scan-local bounded cache
   with **separate** R451 and R457 independent validation domains. R451 and
   R452 share the R451 resource method-shape results; R457 caches its own
   stricter JVM slot-width validation. Errors are never cached.
4. R459 adds opt-in `descriptor_cache_factory` and
   `reuse_opcode_summary` controls. Legacy R459/R460/R461/R462
   behavior is unchanged by default. R463 enables both along with R461
   immutable CP and R462 instruction stream sharing.
5. Existing R446 twice-per-audit complete source/class/dependency SHA
   observations, pinned Store signatures, pinned original v309 JAR,
   bounded nofollow reads, parser parity checks and end-of-pass consistency
   remain untouched. Class files still have three complete bounded reads
   per audit.

## Verification and measurement

The synthetic CI checks:

- Exact R462/R463 public aggregate AND private candidate-worklist parity
  on fake owner trees; default R459 does not invoke the new witness.
- R456 aggregate stage calls from **two per R462 audit to one per R463
  audit**, confirmed with instrumentation. No file-read reductions claimed.
- Descriptor cache hit/miss counts, separate strict parser semantics,
  malformed descriptor refusal and bounded cache growth.
- Invalid, stale, incorrect input-identity and forged count witnesses
  fail closed without a fallback that could silently approve bad evidence.
- Full paired before/after SHA inventories and original-JAR recheck,
  source tamper refusal, no private path or bytes in stdout.
- Two counterbalanced pairs and aggregate-only wall/CPU/read metrics
  on Windows and Ubuntu (Python 3.11 and 3.13).

No real owner-source or full-game input is present in public CI. Real client
performance, full source completeness, asset packaging, JVM loading,
login/gameplay and v312 patch compatibility remain unverified. Timings
include tracing/instrumentation overhead and small fake workloads; they
MUST NOT be extrapolated as a production speedup.

Run in authorized owner workspace only:

    python -B tools/r463/benchmark_metadata_reuse.py --original-v309-jar "<exact owner-local pinned v309 client.jar>" --pairs 2

Read-only; aggregate JSON stdout, no output file. No owner history,
deletion journal, credential, private source or bytecode export. No R421
historical custody approval, no R415/R417 fence changes, no compilation,
deployment, merge or release authorized.
