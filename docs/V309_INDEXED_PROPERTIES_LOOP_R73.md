# R73 — exact original v309 indexed property loop bootstrap witness

The original 697-instruction owner method includes a 22-JVM-instruction protected indexed-array loop with two `invokedynamic` calls for property keys. Both calls reference original bootstrap index **46**, `java/lang/invoke/StringConcatFactory.makeConcatWithConstants`, with descriptor `(I)Ljava/lang/String;` and the same original recipe: a private constant prefix followed by a single integer argument placeholder. Each key is passed independently to `Properties.getProperty(String)`; the non-null path converts a freshly retrieved property to an integer and writes an element of the original integer array.

The repetition matters: the source cannot safely cache the first property lookup in place of the second without changing possible effects. The recipe's **exact original private prefix is not published**; the public [aggregate evidence](../research/v309-source-recovery/indexed-properties-loop-r73.json) records only the recipe form, counts and strict non-certification flags.

`spk_recovery.indexed_properties_loop_r73` checks the complete original-JAR SHA-256 before and after, unique original class entry, exact 22-opcode protected-region size, two equal original `invokedynamic` bootstrap indices, the typed `(I)String` factory call, original `StringConcatFactory` method-handle identity, the one-string recipe with precisely one dynamic integer placeholder, two matching `Properties.getProperty(String)` calls, and one indexed integer array store. It emits a **private original region proof** and a separate count/hash-only aggregate; it deliberately does not fabricate an enclosing source-level Java loop or original method.

Example private replay:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.indexed_properties_loop_r73 `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'C:\private\r73-new-output' `
  --sha256 '<complete original v309 JAR SHA256>'
```

The class entry above is a placeholder and must be resolved privately. Never publish generated private output, recovered strings, or the original JAR.

**Acceptance limits:** The original recipe and 22-instruction window were independently confirmed read-only. The new generic GitHub CLI has not yet been replayed on the complete private original binary, nor has a source-equivalent indexed loop or full 697-instruction method been compiled and certified. Four other complex local protected source regions remain unaddressed, together with the separate 364-instruction method and full runtime parity.
