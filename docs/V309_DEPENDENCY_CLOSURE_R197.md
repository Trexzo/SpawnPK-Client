# R197 — pinned Java dependency classpath inventory

This lane inspects **explicitly approved** external JAR files without running them or using the original SpawnPK game JAR as a dependency. It records per-JAR SHA-256, binary class counts, and duplicate class names across supplied dependencies. Rejects missing approvals, changed bytes, unsafe duplicate entries and class entries in the known `rs/` client namespace. Original/relocated game classes cannot be ruled out merely from their path.

## Private replay

Create a private approval JSON file mapping exact JAR basenames to independently reviewed expected SHA-256 digests. Then run:

```powershell
python tools/dependency_closure_r197.py --jar 'C:\private\deps\one.jar' --jar 'C:\private\deps\two.jar' --approval-json 'C:\private\approved.json' --output 'C:\private\r197-classpath.json'
```

Never approve a dependency merely because a filename or download URL looks plausible. The original client JAR must not be listed. Third-party license and full transitive/classloader closure remain separate requirements.

## Meaning

An absent import may be a library issue rather than failed client deobfuscation. R196 grouped 1,274 uploaded Java source files by their unresolved direct import packages; R197 is a necessary second step to fingerprint actual library binaries rather than guessing their identities. R197 does **not** fetch required JARs, solve transitive Maven/Gradle metadata, check symbol signatures, or compile source. The existing R15 full-source javac count remains **2,002 errors** under its dependency-free diagnostic profile. That figure must not be compared to a future library-resolved build without a labeled profile change.

The uploaded third-party project declared Java 11 and a vendored dependency that was absent from the provided archive. Its build inputs must be independently sourced and verified. This is not yet the exact private original-v309 1,279-source recovery tree.

All hosted tests are synthetic and public-safe; only private inputs can provide authoritative dependencies.

## R197 source-to-approved-JAR import cross-check

`tools/source_dependency_coverage_r197.py` joins the R196 private Java import scan with R197 SHA-checked dependency JAR class inventories. It returns *sampled* per-package direct-import matches and omissions, source archive fingerprint and approved JAR fingerprints. It intentionally marks `complete_package_coverage_proven` false in every group: sampled imports, wildcards, static member imports, Java ABI and transitive classpaths are **not** equivalent to compiler resolution.

Example: `python tools/source_dependency_coverage_r197.py --source-zip PRIVATE-R15.zip --jar APPROVED.jar --approval-json APPROVALS.json --output PRIVATE-COVERAGE.json`.

Dedicated synthetic source/JAR overlap checks run in Ubuntu/Windows CI. This capability does not change the 2,002-error R15 compiler result or certify the original v309 client.
