# v309 source: package/type shadowing in obfuscated dependencies

The complete external v309 candidate source tree has 1,301 Java files (1,270 primary source, 31 resource-provided Java sources). Its last provisional **unmodified source** compile with the SHA-pinned 9,333-class external-namespace capsule returned **118 javac errors** in 36 files.

The most important unresolved imports are not absent from the original v309 JAR. Obfuscated binary names create simultaneous Java types and Java *package prefixes*. During Java source compilation, a package component can instead bind to a class/interface, so otherwise present fully qualified imports fail. No guess about renamed source behavior is needed to diagnose this.

## Source-bound compilation-only suppression

This independent research module examines:
- the exact SHA-pinned original v309 JAR,
- the original SHA-pinned externally supplied build-309 source ZIP,
- the exact output JAR of merged PR #898 and its content-derived research report,
- **non-static Java imports** from the 1,270 candidate source files, and
- all byte-exact collision classes in the original JAR.

It discovers shadow entries from an actual class-file-backed imported type **and** a classfile that occupies one of its intermediate package segments. There are **seven** such intermediate class entries, supported by **86** source import occurrences. Each of the seven candidate shadow classfiles is verified byte-for-byte against the original exact v309 JAR. Any direct import of a class targeted for suppression fails closed.

The tool removes exactly those seven classes **from a separate derived compile-only JAR**, never from the original client or archived candidate source. The new provisional capsule contains **9,326 classes**, down from 9,333. Suppressed class names are calculated locally and **never emitted into GitHub or the aggregate report**.

The result is intentionally **NOT** canonical dependency authority. Non-`rs/` first-party code could exist; source import scanning does not prove there are no reflection calls or dynamic dependencies on those seven classes. The proper runtime JAR is unchanged. This only diagnoses javac's namespace binding.

## Local invocation

Run from a clean SpawnPK-Client checkout with Python 3.11+, using the private files already pinned by #898:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.v309_shadow_compile_research `
  --parent-capsule 'C:\private\capsule\external-namespace-compile-candidate.jar' `
  --parent-report 'C:\private\capsule\COMPILE-CAPSULE-RESEARCH.json' `
  --source-zip 'C:\private\SpawnPk-Decompiled-main.zip' `
  --original-v309 'C:\private\original-v309-client.jar' `
  --out-dir 'C:\private\fresh-shadow-compile-only-output'
```

Private local preflight using the identical collision-derivation rules produced twice byte-identical outputs:

- Derived filtered JAR SHA256: `b27cc8aa5c6227c088901ed4c7f218a9a56f4fd39fa3552ddc3c0ddda6a27293`
- Research-only report ID: `SPKSHADOW7_20ACC689E2995C3849CD`
- 7 verified collisions, 86 import witnesses, 9,326 retained external candidate classfiles, 0 new accepted identities

With that capsule plus the exact Lombok 1.18.32 compiler dependency, the **full 1,301-file unmodified candidate source** Java 11 compiler probe reports **7 errors** rather than 118. The seven are confined to missing external Gson API references and one obsolete/unresolved Apache Commons class reference. Neither needed external class exists in the original v308 or v309 JAR; the source project's Gradle file declares `com.google.code.gson:gson:2.11.0`. This result is still a **failed compile**, not an authoritative compiler frontier, class-set proof or source release.

## Publication and acceptance limits

Do NOT commit the binary capsule, private Java, original source archive, raw compiler error text, class names or private Code/CP data. The verified research report includes only counts, expected hashes and zero-acceptance state.

Current v309 canonical remains `ACCEPTED_INCOMPLETE` (143 unresolved relationships / 26 descriptor blockers / 0 newly accepted class and member IDs). Source M1 for exact v308 remains separately blocked at its last measured 98 javac errors; neither canonical source release directory has been populated.

Further work must provide an independently SHA-verified external Gson dependency and separately audit the one Apache Commons source reference. Removing or patching missing references merely to make javac green is **not** source-recovery acceptance.
