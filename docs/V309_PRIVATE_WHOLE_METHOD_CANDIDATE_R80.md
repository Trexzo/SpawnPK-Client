# R80 — private original 697-instruction Java method-body candidate

The exact SHA-256-pinned original v309 binary was independently inspected. Its 697-instruction properties/settings method partitions into 48 setup/typed property instructions, 560 instructions inside 42 local Exception-protected regions, 42 adjacent `goto` separators, 42 matching `astore_3` catch entries, and five final normal/IOException-return instructions. It contains 78 static writes and 44 typed exception-table entries.

R80 is the first **private candidate Java method-body text stitcher**. It refuses to emit a candidate unless three earlier independent proof families all succeed against the same original JVM profile:

- R77 validates that the eight R67/R68/R71–R76 private source families cover exactly 42 original handler tuples in original order.
- R79 validates the exact 48 original prefix instructions and four direct typed assignments.
- R70 validates the original two-range IOException outer catch and its real printStackTrace side effect.

R80 further requires each source region to be adjacent to precisely one original `goto` skipping one `astore_3` empty-catch entry, with no unexplained inter-region JVM instructions. It includes the 42 source blocks as local `try/catch` statements in an ordinary enclosing Java IOException `try/catch` after the original preflight call.

Usage (requires private outputs from each of the eight verified earlier family tools):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m spk_recovery.private_whole_method_candidate `
  'C:\private\v309-original.jar' 'PRIVATE_OWNER.class' 'PRIVATE_METHOD' '()V' `
  'C:\private\r80-new-output' `
  --original-sha256 'ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38' `
  --site 'R67=C:\private\r67\SITES.private.json' `
  --site 'R68=C:\private\r68\SITES.private.json' `
  --site 'R71=C:\private\r71\SITES.private.json' `
  --site 'R72=C:\private\r72\SITES.private.json' `
  --site 'R73=C:\private\r73\SITES.private.json' `
  --site 'R74=C:\private\r74\SITES.private.json' `
  --site 'R75=C:\private\r75\SITES.private.json' `
  --site 'R76=C:\private\r76\SITES.private.json'
```

The `SITES.private.json` filenames are placeholders for actual private family output arrays, not public aggregate evidence. Private Java method-body text stays local. It is **not** an automatically compilable full owner Java class; nested enums, field declarations, potential Java local variable names and other owner dependencies still need to be supplied as original evidence. The tool does not claim that supplied JSON is authentic absent separate earlier JAR replays. A Java compiler run and R66's original/candidate exact 697-instruction/44-handler/78-write structural parity remain mandatory. Helper side effects and runtime equivalence are also unproven.

No original JAR, source text, literals or obfuscated member identities are committed.
## Independent original JAR bytecode witness (R80)

The pinned original v309 JAR was inspected directly with read-only JVM disassembly and its classfile's 44-entry exception table. For all **42** local Exception protected regions, the source body is contiguous and each end is immediately followed by **one** original `goto` across precisely **one** original `astore_3` catch entry. All original jump destinations land on the next source region (or the final epilogue). **Zero layout mismatches** were found. The exact partition is **48 prefix + 560 protected + 42 gotos + 42 catch entries + 5 tail = 697** original JVM instructions. The first segment contributes four `putstatic` writes, while protected bodies contain the other 74.

The public-safe aggregate is `research/v309-source-recovery/original-697-stitch-layout-r80.json`. This observation supports R80's strict source assembly gate but is not the result of the new R80 private CLI replay. It does not prove that the 42 Java fragments recompile into the original 697-op method, and does not validate handler/operand/side-effect or runtime parity. Original JAR, private member identities and literal configuration strings remain private.
