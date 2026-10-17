# R198 — complete explicit-import closure for private v309 Java candidates

R197 deliberately matched only **up to six sample imports per package**. A match for one sample must never be described as verification of that entire package. R198 reads **every explicit, non-static, non-wildcard import** across the complete private Java archive, and compares it with the Java owners declared by source files and the classes in approved SHA-256-pinned JARs.

Per import, R198 distinguishes `internal_source`, `approved_dependency`, `jdk_namespace_candidate`, `platform_unknown`, and `unresolved`. It supplies source-level and package-level unresolved inventories and preserves ambiguity counts for wildcard and static imports. Exact class names found in a JAR do not prove full method/field ABI compatibility, transitive dependency closure or source compilability. JDK prefixes are candidates, not an authenticated Java 11 module inventory.

Private command:

```powershell
python tools/source_import_coverage_r198.py --source-zip 'C:\private\SpawnPK-R15.zip' --source-prefix 'src/' --jar 'C:\private\verified-library.jar' --approval-json 'C:\private\approved-jars.json' --output 'C:\private\r198-coverage.json'
```

Supply `--jar` once for each independently verified external dependency JAR, or omit it to measure the no-dependency baseline. The tool does not download JARs or substitute stubs. The generated report includes private source paths; do not publish it without review.

The previously measured R15 **2,002 javac errors** are from an intentionally incomplete JDK-only diagnostic profile. R198 by itself is a source-import analysis, **not** a new full-tree compilation or a reduction of that error count. Original-v309 JVM bytecode parity and the separate recovered 1,279-source tree remain unverified.

R198 hosts only synthetic unit tests using invented Java names and synthetic ZIP/JAR members on Linux and Windows.
