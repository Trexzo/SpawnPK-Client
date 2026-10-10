# R37 — v309 private recovered-source frontier

This is the **current measured source-reconstruction status**, recorded
inside the GitHub project without uploading either original client binaries
or unreviewed decompiled Java. The source of truth for the aggregate record:

[research/v309-source-recovery/frontier.json](../research/v309-source-recovery/frontier.json)

## Measured original-v309 configuration candidate

The R24 bounded Java source slice was independently recompiled again with
JDK 21 targeting Java 9 bytecode, producing the **same candidate class
SHA-256** as R24. The original v309 JAR SHA-256 was reverified. The private
original and compiled classfiles were inspected for field/method counts,
JVM major version, class flags, superclass and interface counts.

| Area | Original v309 | Private candidate |
| --- | ---: | ---: |
| Declared JVM fields | 126 | 4 |
| Declared JVM methods | 10 | 8 |
| JVM classfile major | 53 | 53 |
| JVM access bitmask | 0x0031 | 0x0031 |
| Direct interfaces | 0 | 0 |
| Direct superclass | Object | Object |

Of four candidate fields, three match the original field declarations'
JVM descriptors/modifiers; one is missing the original `final` modifier.
The candidate lacks 122 original field declarations.

R24's independently recompiled method-body study demonstrated **seven
instruction-level matches**, with six matching StackMapTable metadata
and one differing. The separate private placeholder body was used solely
to satisfy compilation dependencies; **it is not a recovered method**.
Two original method declarations are absent; together with the placeholder,
three substantive original method bodies remain unrecovered.

R31's later StackMapTable verification is intentionally stricter than
instruction-level matching. **Do not re-label all seven R24 matches as
R31-certified whole methods**. This frontier is bounded historical evidence,
not a pass from any current complete-source acceptance gate.

## Authority and publication status

The configuration owner remains `CLIENT_CLASS_000167` with **unaccepted**
cross-version class lineage. Canonical field/member relationships have not
been promoted. The source file itself remains private. The full original
client is not rebuilt from recovered Java, and neither original behavior
nor runtime equivalence has been established.

Exact original JAR, raw obfuscated coordinates, and private reconstructed
Java must never be uploaded into the public repository or CI artifacts.

## Next engineering frontier

Use R33/R34's private source compile, R31/R32/R35 method/field matrix and
R36 class-header evidence to measure actual Java revisions against the
pinned original, prioritizing the missing class initializer and load/save
method implementations. Any new count must be backed by exact-input replay
and independent regression tests before updating `frontier.json`.
