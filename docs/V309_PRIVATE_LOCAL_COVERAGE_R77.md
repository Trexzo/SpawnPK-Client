# R77 — One-to-one original v309 local protected-region coverage

R77 adds a fail-closed private validation step between individually recovered R67, R68, R71–R76 Java fragments and any future whole-method compilation.

Using a SHA-256-pinned original JAR, it verifies one and the same 697-instruction, 78-write method with 44 exception entries (42 local Exception plus 2 outer IOException). Its private inputs are the eight individual source-site JSON **arrays**, not GitHub aggregate evidence files. It demands each original local exception handler coordinate tuple be accounted for exactly once, rejects duplicate and overlapping protected sites, then orders private fragments by original bytecode position.

Use the module as: python -m spk_recovery.private_local_coverage ORIGINAL_JAR OWNER.class METHOD DESC NEW_OUTPUT --original-sha256 SHA --site R67=PRIVATE_JSON --site R68=PRIVATE_JSON --site R71=PRIVATE_JSON --site R72=PRIVATE_JSON --site R73=PRIVATE_JSON --site R74=PRIVATE_JSON --site R75=PRIVATE_JSON --site R76=PRIVATE_JSON

Private JSON inputs must be produced by each source-family checker against the exact same original binary. Source fragments and original identifiers are never placed in the repository by this tool. The aggregate output retains only count metadata and a digest, and is research-only.

**This is a site-coverage and ordering witness, not a source-equivalence certificate.** Inputs can be forged; provenance still requires independent private tool replay. All inter-site Java statements, the enclosing method and two IOException handlers, exact operand equivalence, helper side effects, nested enums, compilation and runtime verification remain open.