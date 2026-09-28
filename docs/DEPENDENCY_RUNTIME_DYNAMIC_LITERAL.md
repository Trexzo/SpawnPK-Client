# R8DEP28 control-flow-safe literal dynamic targets

R8DEP28 narrows the unresolved dynamic-loading frontier produced by R8DEP27.

It does **not** perform general symbolic execution and it does not infer targets
from string proximity.

A dynamic callsite receives literal target authority only when all of these
conditions hold:

1. the loader API has an exact supported one-target-argument descriptor;
2. the immediately preceding instruction is `ldc` or `ldc_w`;
3. the constant type exactly matches the required target type (`String` or
   `Class`);
4. the invocation offset is not any branch or switch target;
5. the invocation offset is not an exception-handler entry;
6. the predecessor falls through directly into the invocation.

This proves the top-of-stack target argument for the supported single-target
forms without claiming broader data-flow knowledge.

Supported literal-proof forms include:

- `Class.forName(String)`;
- `ClassLoader.loadClass(String)`;
- `MethodHandles.Lookup.findClass(String)`;
- `System.load(String)` and `System.loadLibrary(String)`;
- `Class.getResource*(String)`;
- `ClassLoader.getResource*(String)`;
- `ServiceLoader.load(Class)`.

The classifications are:

- `literal_target_proven`;
- `service_loader_class_token`;
- `native_load_literal`;
- `dynamic_target_unresolved`;
- `native_load_dynamic`.

A ternary or other control-flow merge remains unresolved when the invocation is
a branch target, even if one immediately preceding instruction is a literal
load. Values routed through locals, fields, concatenation, builders, or method
returns remain unresolved.

Private reports may include the proven literal/class target and proof reason.
Public reports retain only stable callsite IDs, category, classification,
invocation kind, and whether literal proof exists.

R8DEP28 remains analysis only. External/native-driven reflection absence stays
unproven and `runtime_capsule_mutation_ready=false`.
