# R153 — original v309 matrix method recovery frontier

R150 #1037, R151 #1038 and R152 #1039 have passed full GitHub Recovery CI and their dedicated Ubuntu/Windows tests. Their private Java method reconstructions account for **13 previously investigated original matrix method bodies / 350 matching decoded instructions**, but these reported matches remain independent private evidence pending replay through the exact repository verifier. This tool does **not** mark those methods accepted.

R153 takes the exact SHA-pinned original-v309 client Jar and a fresh private method-selection JSON (the thirteen earlier investigated original name/descriptor identities). It checks via R136 that the target non-rs matrix class is genuinely excluded because it depends on original `rs/` game classes. It parses **every** original matrix method from the trusted JVM classfile profiler and accounts for exactly one of: (a) previously selected but not reverified, (b) unselected with direct original Packet references (including only-in-descriptor types), (c) unselected with another direct `rs/` descriptor/member reference, or (d) unselected with no such direct reference. It counts unselected original method invocations of Packet and remaining decoded instructions without printing original member names or binary contents. A direct-reference absence does not certify indirect callgraph independence or safety.

Private command:

```text
python -m spk_recovery.private_v309_matrix_method_coverage_r153 PRIVATE_ORIGINAL_V309.jar PRIVATE_13_METHOD_SELECTION.json FRESH_PRIVATE_REPORT.json --selection-sha256 EXACT_SELECTION_SHA256
```

Expected original JAR SHA-256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The prior private 13-method selection SHA was recorded in issue #1004, but the report requires actually supplying and hash-checking that private file.

Synthetic Ubuntu/Windows Java 11 tests build independent `rs.Packet`, `rs.Game` and `ext.Matrix` classfiles. They verify exhaustive selected/unselected counts, a direct Packet invocation, a **descriptor-only Packet dependency**, another rs-dependency, and SHA/selection mismatch aborts. This is a **read-only frontier inventory**, not an original game binary compiler fallback, source code recovery of the remaining methods, or proof that 516 outstanding Java compiler errors have changed.

Next: use the exact private R153 categorized result to choose the remaining non-Packet matrix methods for independent Java source implementation and method-by-method instruction parity; handle Packet loader only after call-edge/name corroboration. No private source or original binary is published.
