# v309 exact constant-pool referent-aware method research

This is a **bounded first implementation** for [#877](https://github.com/Trexzo/SpawnPK-Client/issues/877), not canonical proof of a changed class. It composes the repository's established JVM bytecode-profile parser; it does not create a new parser or publish private client code.

The existing v309 frontier remains `ACCEPTED_INCOMPLETE` with **143 unresolved field identities**. The earlier class candidate tools #875 and #876 compare globally unique strings and method shapes. This lane addresses a separate problem: **the same JVM bytecode constant-pool index can mean a different member or literal between two JARs**, and equivalent referents can occupy different indices.

## Strict research boundary

- Verify the tracked field report and class lineage against SHA-pinned frontier inputs, and require both original exact private v308/v309 client JAR SHA-256s.
- Restrict analysis to exactly eight unaccepted descriptor-class research pairs; verify each canonical v308 class entry and structural fingerprint before profiling.
- Reuse `bytecode_profile.profile_class_field_accesses()` for decoded method instructions, CP member and type owners, bootstrap handles, and exception tables.
- Compare normalized opcode, exact Code length, control-flow offsets, local/immediate operands, exception handlers and CP referent **meaning**. Strip *only* irrelevant CP slots and bootstrap attribute order. The sole rename alias is the **explicit proposed class owner** old→new; third-party owners and member names remain exact and conflicting referents veto equality.
- Handle `invokedynamic` only when its bootstrap method, call descriptor and supported arguments are fully resolved. Refuse unknown bootstrap tags, unresolved MethodHandle/MethodType/condy LDC, switch tables, multidimensional arrays and instructions with unsupported multi-byte operands; never silently ignore them.
- Count only CP-bearing, code-bearing methods whose complete normalized fingerprints are individually unique on **both** sides. Duplicate signatures, constructor/static initializer code and CP-free methods **never** count as unique referent witnesses.
- Export only aggregate counts per eight logical class identities. Do not export decoded instructions, CP values, literal digests, method names, private Code arrays, raw classfiles, full indexes, or accepted mappings. The output must be a new, nonclobber research file.

**Important limitation:** this is a **pairwise** proposed old-class→new-class diagnostic. It does not test competing classes across both full archives and is **not independently sufficient** to authenticate canonical class or member identity. The companion whole-archive alternative search, richer rename-aware semantic comparisons and explicit review remain tracked in #877.

## Private invocation

From a matching checkout with the two locally held private exact JARs:

```powershell
python -m spk_recovery.v309_cp_method_referent_research `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out "$env:TEMP\v309-cp-method-research-new.json"
```

Those paths are illustrative. Never put proprietary client archives or private report internals in a PR.

Synthetic tests cover CP-index shifting with identical referents, equal CP slots with different literal or member meanings, duplicate signatures, unresolved MethodHandle LDC, missing/ambiguous `invokedynamic` bootstrap arguments, class-owner renames, unsupported opcodes and changed exception handling. A `javac --release 11` fixture builds actual classfiles with shifted CP layout and checks the normalized method fingerprints.

Do not close #877 or reduce the official 143 count as a side effect of this tool; follow-up independent evidence and reviewed acceptance remain required.
