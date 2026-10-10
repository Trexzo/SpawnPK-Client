# R26 — exact original-JAR class slice for CFR / Vineflower

This is an in-repository alternative to decompiling the entire client JAR.
The existing `spk_recovery.decompiler.run_decompiler` accepts a JAR input
for both CFR and Vineflower; R26 produces a minimal **private JAR input**
containing one exact original class plus its `$Nested` classes.

## Private replay from the repository root

Set Python's module path to `src`, and use your own exact original client
JAR path. For v309 the accepted frontier currently pins SHA-256
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m spk_recovery.exact_class_slice "C:\private\client-v309.jar" "rs/f/a.class" "C:\private\config-v309-slice.jar" --original-sha256 "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
~~~

Pass `config-v309-slice.jar` as the `input_jar` to the existing
`spk_recovery.decompiler.run_decompiler`, first with `engine="cfr"`
and then separately with `engine="vineflower"`. Each engine must have
a verified executable tool JAR and its own fresh, private output directory.
No CFR/Vineflower binary or download is provided by this change.

## Safety and limitations

- Refuses changed original JAR hashes, invalid paths, missing or duplicate
  original class entries, invalid JVM magic, output overwrite and writes
  aimed at the original JAR.
- Emits deterministic ZIP bytes in name order with a fixed timestamp,
  preserving each selected `.class` file's **exact input bytes**.
- Includes only `A.class` and `A$*.class` for a requested `A.class`;
  it does **not** invent accepted aliases, infer wider dependencies or
  guarantee that generated Java will compile without additional classes.
- Does not overwrite canonical source files or mutate member/class lineage.
- A class slice **contains proprietary original bytecode**. Keep both
  the slice and generated Java privately on the local computer.
  Never commit them to GitHub, CI artifacts or a public issue.
- Original-client replay and third-party decompiler execution are separate
  proof steps; hosted CI uses only synthetic Java fixtures.

The tracked `CLIENT_CLASS_000167` owner and three remaining configuration
field candidates retain their unresolved identity vetoes. Successful
decompilation alone is **not** formal class or member identity acceptance.
