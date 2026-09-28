# R8DEP29 dynamic target classification

R8DEP29 classifies literal dynamic targets already proven by R8DEP28 against
exact runtime authorities. It does not create new target guesses.

Inputs are private identifier-bearing R8DEP28 dynamic authority, private
R8DEP11 replacement authority, private R8DEP26 resource authority, and the
exact bundled/readable JAR.

## Class-loading literals

String literals from supported class-loading APIs are converted from valid JVM
binary names to internal names only when every name segment is syntactically
valid. Slash-form strings, array descriptors, malformed names, and alternative
nested-class spellings are not guessed.

A normalized class target is classified as:

- project-owned;
- dependency `official_replaceable`;
- dependency `residual_bundled`;
- dependency `project_retained`;
- dependency `platform_runtime`;
- bundled but unclassified;
- multi-release-only bundled and unresolved;
- platform runtime;
- non-bundled unresolved;
- malformed.

ServiceLoader class tokens use their exact proven internal class identity, but
provider discovery remains explicitly unproven.

## Resource literals

For `Class.getResource*`:

- a single leading slash means an absolute classpath entry and is stripped;
- a relative literal is resolved against the exact caller package.

For `ClassLoader.getResource*`:

- a non-leading-slash literal is treated as the exact classpath entry;
- leading-slash semantics remain unresolved rather than normalized.

Dot/dot-dot path segments and backslashes are rejected from exact resource
classification.

Resolved resource paths are bound to private R8DEP26 resource authority where
available, otherwise exact bundled resource presence is reported separately.

## Native literals

A proven `System.load` or `System.loadLibrary` literal is recorded only as a
native runtime requirement. It is not artifact/classifier equivalence.

Public reports use stable IDs and counts. Private reports may include exact
literal targets, normalized class targets, resource paths, and caller/API
identity.

`runtime_capsule_mutation_ready=false` remains mandatory.
