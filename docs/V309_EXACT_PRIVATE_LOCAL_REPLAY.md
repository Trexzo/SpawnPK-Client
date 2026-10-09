# v309: one-command exact-private research replay

This is a **local-only execution wrapper** for the existing merged spk_recovery.v309_exact_private_concordance_replay Python module. It is not a new evidence engine, mapping acceptance tool, or updater. Five-lane research and whole-archive rival vetoes remain owned by the existing Python modules.

From a current SpawnPK-Client checkout on Windows, supply the two original SHA-pinned v308 and v309 JAR paths:

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-V309ExactPrivateFiveLaneReplay.ps1 -V308Jar 'C:\path\to\original-v308.jar' -V309Jar 'C:\path\to\original-v309.jar'

The launcher verifies the protected GitHub frontier (ACCEPTED_INCOMPLETE, 143 unresolved / 26 descriptor-blocked), SHA-256 of both original client JARs, required repository inputs and Python 3.11+. It then uses the existing one-shot in-process builder and produces a new privacy-bounded aggregate JSON outside the checkout, under Desktop\SpawnPK-v309-private-research. It never silently overwrites a result, modifies the binaries or Git repository, accepts a mapping, or uploads private material. A nonzero exit or inconsistent output fails closed.

A successful aggregate result is research-only. Independently inspect per-class pairwise CP witnesses, supported/unsupported method coverage, ambiguity and whole-archive rivals. The next separate proof/acceptance stages must still establish class identity, review member/field relationships, and update canonical lineage explicitly. Nothing in this script reduces the 143 unresolved fields, modifies Source M1's last measured 98 compiler errors, or certifies v309 as current accepted authority.

Keep original JARs, literal/CP indexes, decompilation, bytecode and raw private logs off GitHub. Only publish bounded reviewed aggregate evidence. Hosted Ubuntu and Windows CI cannot run the exact-private JAR replay because the original JARs are not in the repository.
