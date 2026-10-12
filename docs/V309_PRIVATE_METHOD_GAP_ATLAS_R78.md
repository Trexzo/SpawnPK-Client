# R78 — private whole-method original JVM gap atlas

R77 checks that recovered local source-fragment sites cover all 42 distinct original v309 Exception-protected regions. R78 proceeds to partition the **entire** original 697-instruction method instead of assuming local source coverage means complete method recovery.

The private verifier calls R77's handler membership gate on original-JAR-derived profiles and the same eight private family JSON outputs, then labels each JVM instruction as one of:
- within a specific source-family protected region (R67/R68/R71–R76),
- an original local catch-handler entry, or
- not yet covered by the protected source fragments.

It records all original instruction positions exactly once, including 78 static-field writes and original private operand records, in a private JSON atlas. Aggregate reporting includes only counts, sizes and a digest. Outer IOException handling and intervening statements remain outside the locally recovered source family.

Example usage (supply the real private original path, method and eight existing site JSON inputs):

    python -m spk_recovery.private_method_gap_atlas ORIGINAL_JAR PRIVATE_OWNER.class METHOD "()V" NEW_PRIVATE_OUTPUT --original-sha256 WHOLE_JAR_SHA256 --site R67=PRIVATE_JSON --site R68=PRIVATE_JSON --site R71=PRIVATE_JSON --site R72=PRIVATE_JSON --site R73=PRIVATE_JSON --site R74=PRIVATE_JSON --site R75=PRIVATE_JSON --site R76=PRIVATE_JSON

This program does NOT generate hypothetical Java code for gap instructions, does NOT turn empty catches into evidence of original authorial source, and does NOT establish complete structural or runtime parity. Real original-JAR replay and the R66 whole-compiled-candidate parity gate are still mandatory.

No private Java fragments, class names, literal configuration keys, original JAR or private opcode atlas are committed to GitHub.
## Independent original-binary measurement (not R78 replay)

Read-only inspection of the SHA-pinned original v309 JAR verified the real 697-op method directly. Of its instructions, 560 fall inside the 42 original local protected source regions, 42 are local catch-entry instructions and 95 are outside both. The 95 comprise one 48-op setup/direct-property-write prefix, 42 individual inter-region `goto` separator instructions, and a five-op normal/IOException return suffix. Across all 78 static writes, 74 are inside the protected regions and four in the prefix. The 44 exception-table entries and 120 explicit branches were verified against the original.

The public-safe aggregate evidence is `research/v309-source-recovery/original-method-gaps-r78.json`. The original client was found in the user's private Library; no private class identifiers, String keys, disassembly, original JAR or literal operand values were published. R77 and R78 generic source-site replay on that original input is **not** claimed; this is a separate direct-read disassembly measurement.
