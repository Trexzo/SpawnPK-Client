# R25 — source method parity gate (research-only)

This utility lives in Trexzo/SpawnPK-Client and compares two explicitly selected
local JARs: the exact original client and a separately compiled Java source
candidate. It never modifies either JAR or canonical lineage.

## Verified surfaces

- Exact SHA-256 of both JARs and exactly one matching class entry per JAR.
- Exact internal class name and method descriptor; no automatic owner aliasing.
- Method access and decoded JVM opcode / all supported instruction operands,
  including locals, constants, branch targets and switch arms.
- Resolved constant-pool member references, not raw CP numeric positions.
- Resolved invokedynamic bootstrap handles and supported argument types.
- Exception handler entries and method Code lengths.
- JVM Code `max_stack` and `max_locals`, requiring exact valid unsigned-u2 values on both sides.
- Normalized JVM `StackMapTable` presence and frame contents. Object verification types resolve to actual class names rather than raw constant-pool positions; missing or malformed frames fail closed.

Unsupported constants, opcodes, missing bootstrap references, malformed
classfiles and changed input hashes are rejected instead of ignored.

## Local usage

With Python 3.11+ and the repository cloned, set PYTHONPATH to its src directory.
Invoke the module using one command (substitute your paths and measured hashes):

~~~powershell
python -m spk_recovery.source_method_parity "C:\private\original-v309.jar" "C:\private\candidate.jar" "example/Config.class" "someMethod" "()V" --original-sha256 "<original SHA256>" --candidate-sha256 "<candidate SHA256>" --out "C:\private\review-new.json"
~~~

The report uses exclusive-create mode; it never overwrites an existing file.
Without --out, aggregate results are printed without proprietary names.
Keep original JARs, recovered Java and private coordinate tables out of GitHub.

## Explicit authority boundary

CANDIDATE_INSTRUCTION_PARITY is a research classification, NOT a certified
source rebuild, class equivalence, runtime equivalence, or canonical identity.
The parser compares StackMapTable frame encodings and resolved verification
types, but does **not** independently prove that the JVM would verify and run
the methods equivalently. Other Code subattributes and annotations remain
unverified. It also does not prove callee behavior or class-initializer effects.

The blocked v309 CLIENT_CLASS_000167 identity and its three unresolved fields
remain blocked. This tool has no R3M transfer path, no lineage mutation and
no source publication action. Only independently reviewed accepted lineage
and the existing formal promotion gates can change that status.

CI tests use synthetic Java and require hosted Ubuntu and Windows results.
