# v309 JVM array and switch operand proof (research only)

The private exact-JAR audit for issue #877 found 347 primitive newarray sites, seven multianewarray sites, seven tableswitch sites, and seven lookupswitch sites **per build across the eight descriptor-blocked proposed class pairs**. Prior CP-semantic method research excluded methods containing any such opcode, instead of silently treating incomplete operand parsing as equivalence.

## Strict operand proof

The shared bytecode decoder now resolves and validates:

- JVM newarray: exact primitive atype 4..11, distinguishing boolean/char/float/double/byte/short/int/long arrays without a constant-pool index.
- JVM multianewarray: exact CONSTANT_Class array type descriptor and unsigned dimension count (1 through the actual array rank), with full old/new self-class-owner alias normalization where applicable.
- JVM tableswitch: all signed low/high case bounds, every case arm target, default branch target, zero padding, bounded encoded length, and target instruction-boundary validation.
- JVM lookupswitch: every signed case key and branch target, strictly sorted unique case keys, default target, zero padding, bounded encoded length, and instruction-boundary validation.
- Strict fail-closed parsing of truncated/oversized switch tables and malformed array operands before any method can qualify as a CP-referent witness. Legacy jsr/ret/jsr_w subroutines remain explicitly excluded.

The v309 CP method research now compares complete array/switch operand semantics instead of discarding methods merely because those opcodes are present. Existing conservative requirements remain: code-bearing ordinary method only, at least one supported CP-bearing instruction, full Code length and exception-handler shape, exact opcode/address/descriptor/reference meaning, no duplicate method identity witnesses. A CP-free switch or newarray method still cannot cast an independent identity vote.

## Verification

Hosted synthetic tests compile an actual Java 11 classfile containing both Java switch lowering modes, primitive int/long arrays and a two-dimensional array. Positive assertions confirm exact decoded operands; negative tests reject changed case targets, broken padding, unordered/duplicate case keys, invalid dimensions, nonarray CP owners, bad primitive type codes, and unsupported legacy control flow.

Original private JARs and raw bytecode/method names/constant-pool values never enter GitHub; any exact-private replay remains local. These decoder changes alone DO NOT establish a class or field identity or authorize canonical lineage updates. The protected v309 frontier remains ACCEPTED_INCOMPLETE with 143 unresolved fields, including 26 descriptor-blocked relationships. Independent, reviewed acceptance is a separate step.
