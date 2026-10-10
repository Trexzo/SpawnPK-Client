# R39 — exact-hash decompiler tools for local source recovery

The repository already has:
- R26: isolate the exact original client class and nested types
- R27/R29: execute CFR and Vineflower separately with bounded timeouts
- R31/R32/R35/R36: compare recompiled Java against exact original JVM evidence

The remaining practical dependency is supplying **actual runnable decompiler
JARs**. R39 provides a local *acquisition-only* helper that downloads two
specific versioned artifacts from **official Maven Central** over HTTPS,
requires an independently obtained **exact SHA-256**, checks JAR structure
and Main-Class manifest, then saves each executable JAR **without running it**.

## Fixed versioned coordinates

- CFR 0.152:
  https://repo.maven.apache.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar
- Vineflower 1.10.1:
  https://repo.maven.apache.org/maven2/org/vineflower/vineflower/1.10.1/vineflower-1.10.1.jar

Acquire trusted 64-character full-JAR SHA-256 values separately from the
upstream official Maven Central .sha256 sidecars or your independent
verification record. **A version string is not a content hash.** The
acquisition script refuses to download without caller-supplied pins.

Run from the clone root on a machine with Python 3.11+ and HTTPS access:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.decompiler_tool_acquire `
  cfr 'C:\private\decompiler-tools\cfr-0.152.jar' `
  --sha256 '<EXACT_CFR_JAR_SHA256>'
python -m spk_recovery.decompiler_tool_acquire `
  vineflower 'C:\private\decompiler-tools\vineflower-1.10.1.jar' `
  --sha256 '<EXACT_VINEFLOWER_JAR_SHA256>'
~~~

These commands **do not execute** either decompiler or inspect the private
client. They only prepare verified external tooling for later use with
`spk_recovery.dual_decompiler_slice`. R27/R29 independently reverify the
full tool-JAR hashes before invoking Java.

If an upstream Maven distribution is a library-only JAR without an
executable Main-Class, R39 rejects it. In that case obtain a standalone
*executable* release artifact by an independently verified method and supply
it directly to R27. Do not bypass the executable-JAR check or pinning.

## Safety rules

- Only the two hard-coded official HTTPS URLs above can be used.
- Rejects changed tool SHA-256, redirected origin, unexpected engine name,
  non-executable/corrupt JAR, excessive response size, and network failure.
- Creates output exclusively, never overwrites an existing tool or deletes
  files that existed before the command.
- On a failed new acquisition, deletes only that attempt's untrusted partial.
- No original client JAR, decompiled Java or original bytecode coordinates
  are published or transferred to CI.
- Hosted regression tests use synthetic ZIP fixtures with mocked responses;
  no real Maven download or CFR/Vineflower decompilation is claimed.
- Actual dual-decompiler runs and method-level source equivalence are separate
  tests. Successful tool acquisition is not canonical class/field acceptance.

R22's actual original-v309 dual-decompiler execution remains pending until
both *standalone executable* tool JARs and their pins are available locally.
