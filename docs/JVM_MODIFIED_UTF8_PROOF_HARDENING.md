# JVM classfile parser identity-proof hardening (research)

The exact pinned private v308 and v309 archives each contain **27 CONSTANT_Utf8 entries using JVM special two-byte NUL encoding** (C0 80) plus **one UTF-16 surrogate code unit without a paired surrogate**. The old permissive UTF-8 decoder lost this information, potentially making distinct member, literal or class identifiers appear equivalent.

## Implemented behavior

- Both existing parsers (classfile and bytecode_profile) use the **same strict JVM Modified UTF-8 decoder**. It decodes C0 80 as NUL, valid surrogate pairs as supplementary Unicode, and preserves lone UTF-16 surrogate code units **losslessly**. It rejects malformed, truncated, overlong, literal-zero and four-byte standard UTF-8. It never substitutes U+FFFD for failed decoding.
- The existing structural SHA-256 byte canonicalization remains unchanged for all ordinary Unicode; surrogatepass prevents the exceptional UTF-16 code unit from becoming a parser failure or replacement character. Previously pinned lossy structural fingerprints involving exceptional strings must be treated as **incomparable until explicitly reviewed**—never silently rewritten.
- Indexed JSON remains valid UTF-8 and round-trippable. Only lone surrogate code units are written as JSON backslash escapes.
- The existing bytecode decoder rejects all reserved JVM Code opcodes 0xCA..0xFF rather than pretending they are one byte long. Invalid wide nested opcodes, including legacy ret (not fully modeled in research), fail closed.
- invokeinterface now verifies exact JVM argument slot count, including receiver and two-slot long/double types, along with its mandated zero reserved byte. Malformed JVM method descriptors are rejected.
- Synthetic tests and a real javac --release 11 classfile fixture cover modified NUL, supplementary and lone surrogate text, malformed constants, reserved opcodes, invalid interface slot counts and lossless index serialization.

## Evidence and authority limits

This is **parser correctness**, not permission to accept a changed class or field. All existing canonical lineage and research/v309-field-recovery/frontier.json remain untouched at **143 unresolved / ACCEPTED_INCOMPLETE**. Structural-hash consistency must be re-evaluated against the private originals, particularly where the formerly lossy decoder affected literal strings. Any resulting mismatch is a **veto** pending a separate reviewed authority migration; no automatic regeneration or promotion.

The JARs, proprietary method instructions, raw constant-pool values and recovered source remain private. Only bounded aggregate statistics and synthetic Java fixtures can appear in GitHub.

Related: issue #877, pair-local CP semantic evidence #878, whole-archive rival veto #879.
