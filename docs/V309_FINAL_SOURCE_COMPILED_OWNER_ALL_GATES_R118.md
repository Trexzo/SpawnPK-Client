# R118 — one SHA-pinned source-compiled v309 owner must pass R95 + R94 + R58 + R88

## Why another combined gate?

The independently reconstructed original-v309 owner now compiles with **all 126 fields, all four source-legal enums, all ten original owner method instruction shapes (1,348/1,348), 139 branch sites, 45 typed handlers and all 93 initializer writes**. R113/R116 restored the saver ten original StackMap frames. R114/R117 verified all 697 loader operands and reconstructed 161 original loader verification states at the source compiler's corresponding JVM instruction ordinals. R117's standalone private candidate is still a **source preimage**: it has one Java-source-invalid fourth-enum class identity and exactly **two original synthetic String getter accessor callsite names** awaiting R105, plus the three-value enum's known R106 StackMap repair. Passing both large-method gates is therefore NOT full owner acceptance.

## R118 executable strict private acceptance chain

`spk_recovery.private_one_final_original_owner_r118` accepts two **distinct complete SHA256-pinned JARs** (read-only original v309, separately Java9 source-compiled and R116/R117 metadata repaired candidate) and one explicit source-legal fourth enum name. It checks original vs candidate Java9 owner name/access/super, **126 source declarations and ten exact original owner method names/access/descriptors**. The two ZIPs must have **exactly four local nested classes**, with the sole pre-rebind difference being the source-illegal fourth enum class name. It also requires the input candidate's original 364 saver to pass **R113 (364 JVM operands, ten original frames)** and the original 697 loader to pass **R66/R81 (697 JVM operands, 120 original branches, 44 typed handlers, 78 static writes), including all 161 original symbolic verifier states at matching instruction ordinals**.

Then on that **one candidate postimage**:

1. **R106 → R105 → R104 → R95:** reconstruct the exact original three-value enum full-frame, rename the two accessor JVM method declarations and their owner callsites by the original private field targets, restore the source-invalid fourth enum binary name and six original owner `InnerClasses` rows, then demand exact four-enum R95.
2. **R113 + R81 again:** verify that fourth-enum constant-pool/member rebindings have not altered either large owner method's JVM operands or original verifier metadata.
3. **R94:** require **nine complete original ordinary owner methods / exactly 1,135 JVM instruction operands** on that final, unchanged SHA-pinned binary.
4. **R58:** create *exact identity-only* private JVM aliases from the **93 original own-class `putstatic` targets** and recompare all **213 initializer instructions, 93 original static field writes, branch CFG and symbolic method/field/indy operands** on that same postimage. No candidate/original field rename is allowed after rebinding.
5. **R88:** require **126 original and candidate fields, 10 original and candidate methods, four original and candidate nested enum classfile identities, zero missing/extra/drifting declarations**, and strict header parity.
6. **Atomic private promotion:** only if every one of the above gates passes, promote one accepted final SHA-pinned private JAR and sanitized counts/hashes. Failed source proof or any unsupported binary drift leaves no accepted output.

The hosted synthetic composition tests verify input pins, exact four-enum collision, no missing owner method, final R106/R95 failure, final R94/R58/R88 failure, missing large-method verifier parity, and that only **one final candidate JAR** reaches every final gate. They do NOT execute the original v309 binary and do not replace the locally private actual-original CLI replay.

## What success would and would not certify

Passing actual-original R118 would certify a **bounded source-compiled JVM original-owner declaration/operand/control-flow/verification-state parity**, including the four nested enum classfiles. It would **not** prove original authorial Java source identity, external dependency/helper implementations, original configuration filesystem behavior, callback effects, whole network/client runtime, or gameplay equivalence. The original JAR, original-derived method/field names, original string literals and private source Java must NEVER be published.

**Actual private original-v309 R118 CLI has not yet passed.** This is a strict integration tool awaiting the original and source postimage replay, not a success claim.

Private CLI:
`python -m spk_recovery.private_one_final_original_owner_r118 ORIGINAL_V309.jar SOURCE_R117_REPAIRED.jar OWNER.class Surrogate NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 SOURCE_SHA`.
