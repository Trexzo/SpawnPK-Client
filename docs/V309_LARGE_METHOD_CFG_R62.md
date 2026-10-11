# R62 — exact original-v309 large-method CFG recovery frontier

After R60 identified six bounded short method source forms and R61 established the four-instruction LambdaMetafactory consumer boundary, two original owner methods remain large and unreconstructed.

## Grounded original-JAR measurements

Read-only disassembly of the SHA-256-pinned original v309 JAR found:

| JVM feature | Larger method | Other method |
| --- | ---: | ---: |
| JVM instructions | **697** | **364** |
| `putstatic` writes | **78** | 0 |
| Original exception-table entries | **44** | 1 |
| Explicit branches | **120** | 9 |
| `goto` | 77 | 2 |
| `ifnonnull` | 33 | 0 |
| `invokedynamic` | 2 | 46 |
| `invokevirtual` | 132 | 102 |

The 697-instruction method also has 47 `invokestatic` calls, six `ifnull`, two `ifeq`, one `ifne`, and one `if_icmpge`. These are exact **bytecode observations**, not proof of a JSON/config format, a Java try/catch tree, or the values assigned to the 78 fields. The source opcode-stream hashes and truthful certification vetoes are recorded in [R62 aggregate evidence](../research/v309-source-recovery/complex-method-cfg-frontier-r62.json). Actual original identifiers and literals remain private.

## Reusable GitHub tool

`spk_recovery.large_method_cfg_atlas` takes a complete original JAR, a **private exact class entry and method signature**, and an unused private destination. It checks the whole-JAR SHA-256 before/after, unique owner classfile, exact selected method identity, contiguous instructions spanning its original code length, valid branch targets, valid exception-table bytecode offset boundaries, and declared target metadata for every owner `putstatic`.

It partitions the method into bounded **basic blocks** at entry, branch targets and fallthroughs, exception-region boundaries, and exception-handler entry points. It retains original full branch targets and handler regions, plus ordered static field targets with a small preceding-opcode window, in `original-method-cfg.private.json`. `original-method-cfg.aggregate.json` includes only counts and a SHA-256 of that private atlas. No guessing of `try/catch` source, dataflow semantics, default values, or mapping identities is permitted.

From an actual GitHub checkout (example coordinates are placeholders):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.large_method_cfg_atlas `
  'C:\private\original-v309.jar' `
  'example/OriginalOwner.class' `
  'privateOriginalMethodName' '()V' `
  'C:\private\r62-new-output' `
  --sha256 '<complete original JAR SHA256>'
```

Private outputs must never be committed to GitHub: they contain original class/member names and bytecode offsets. The tool generates no source code, and passing its control-flow inventory is **not** a reconstructed method.

Hosted synthetic Java9 tests cover a branched method with a real JVM try/catch table and static writes, malformed handler entry offsets, noncontiguous method bytes, missing method signature, incorrect complete JAR pin and existing private output paths.

## Honest next gate

To turn the 697-instruction method into Java, preserve and verify its 44 exception regions, 120 branch edges and all 78 writes with exact values and helper call side effects. The 364-instruction method must independently restore its invokedynamic bootstrap and object setup behavior. The R62 GitHub tool has not yet been replayed against the original client; independent read-only JVM analysis supplies the currently tracked measurements. Source and runtime equivalence remain false.
