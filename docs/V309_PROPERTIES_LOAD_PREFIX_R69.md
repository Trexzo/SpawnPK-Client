# R69 — exact original-v309 File and Properties load Java source prefix

R67–R68 reconstruct 31 local protected assignment source blocks but originally kept `originalLocalSlot1` as an unresolved Java type placeholder. R69 provides original JVM proof that local slot 1 is **`java.util.Properties`**, initialized once, and recovers the complete **first 24 JVM instructions** of the 697-instruction settings-loading method as a private Java source prefix.

## Original JVM-backed source

Original instructions are an exact contiguous 24-opcode sequence: static preflight; `new File` from an original owner static String; `File.exists()` and conditional early return; `new Properties`, its constructor and store into JVM local1; `new FileInputStream` from local0 stored in local2; `Properties.load(InputStream)`; then `FileInputStream.close()`. This exact constructor/field/helper/stream member data is read from the pinned original class, not guessed.

Private generated source has this structure (original field/member identifiers stay private):

```java
originalPreflight();
java.io.File originalLocalSlot0 = new java.io.File(originalStaticFilePath);
if (!originalLocalSlot0.exists()) return;
java.util.Properties originalLocalSlot1 = new java.util.Properties();
java.io.FileInputStream originalLocalSlot2 =
    new java.io.FileInputStream(originalLocalSlot0);
originalLocalSlot1.load(originalLocalSlot2);
originalLocalSlot2.close();
```

Original bytecode has exactly **one `astore_1`** for this method and **82 calls to `Properties.getProperty(String)` plus one call to `getProperty(String,String)`**. Thus R67/R68's original lookup receiver is now typed, though full source compilation and exception behavior remain unresolved.

## Outer IOException boundaries

Two original `java.io.IOException` table entries share a handler. Their protected byte offsets start at **3** and **22**, ending at **21** and **1605** respectively. Their exact *Java catch scope, values and side effects are not yet reconstructed*. R69 explicitly does NOT substitute `try-with-resources` or invent equivalent exception/finalization behavior.

## Actual GitHub module and tests

`spk_recovery.properties_load_prefix_source` verifies the original whole JAR SHA-256 pre/post, exact private owner/method and declared preflight/static path field, exact 24-op contiguous prefix and branch target, exact File, Properties, FileInputStream construction and calls, and the single JVM local1 store. It generates private Java source only in a fresh private directory, with a separately shareable counts/SHA report. No original path String, obfuscated member, source or binary is publicly published.

Synthetic Java9 tests compile the original prefix with the real Java I/O and Properties classes, reconstruct the private source, recompile it, and compare the first 24 original/candidate JVM opcodes. They reject a mutated Properties constructor class, a changed stream-close call, a wrong JAR pin, and an occupied output location.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.properties_load_prefix_source `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'privateOriginalMethod' '()V' 'C:\private\r69-new-output' `
  --original-sha256 '<whole original JAR SHA256>'
```

The private original coordinates are illustrative placeholders. Public-safe evidence is in [`properties-file-prefix-r69.json`](../research/v309-source-recovery/properties-file-prefix-r69.json).

## Important nonclaims

The new R69 CLI has **not** yet been replayed against the actual private original-v309 JAR; observations come from independently inspected exact original bytecode. The recovered fragment alone does **not** compile as the whole original 697-instruction method. The full outer IOException handler, other 11 local protected regions, helper method effects, original method compilation and runtime parity remain open.
