# Chat 2 — exact-v308 plugin framework semantics R17

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R17 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R16 review batches.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_16DAA16126896ADC855E`
- field/method proposals: **0**

## Plugin base and descriptor

- `rs/s/a` -> `Plugin`
- `rs/s/e` -> `PluginDescriptor`

The base class is abstract, implements Guice Module, owns an Injector, exposes lifecycle
hooks and is the direct superclass of all reviewed runtime plugin implementations. Its
display-name accessor reads `rs/s/e` directly from the concrete plugin class.

`PluginManager` contains surviving exact diagnostics:

- `Class {} has plugin descriptor, but is not a plugin`
- `Class {} is a plugin, but has no plugin descriptor`
- `Plugin {} is now running`
- `Plugin {} is now stopped`

The descriptor is a runtime TYPE annotation carrying plugin title/group/description,
string-array metadata and lifecycle/visibility booleans.

## Dependency annotations

- `rs/s/d` -> `PluginDependency`
- `rs/s/c` -> `PluginDependencies`

`PluginDependency` is a runtime TYPE annotation whose value is
`Class<? extends Plugin>`. It is itself marked `@Repeatable` with `rs/s/c` as the
container annotation.

`PluginManager` reads these annotations while constructing the plugin dependency graph,
and its exact diagnostics include dependency cycles and unmet dependencies.

## Loading and failure boundary

- `rs/s/b` -> `PluginClassLoader`
- `rs/s/f` -> `PluginInstantiationException`

The classloader extends URLClassLoader, loads from a plugin File and falls back to a parent
ClassLoader when local lookup fails.

The exception type is used by PluginManager to wrap plugin construction, Guice child
injector creation, dependency-graph errors and plugin start/stop failures.

## Root client configuration

- `rs/s/h` -> `RuneLiteConfig`

This interface extends Config and carries exact `@ConfigGroup("runelite")` metadata.
Its configuration surface includes window settings, overlay settings, notification settings,
focus requests, notification flash behavior, hotkeys and other client-level controls.

## Acceptance boundary

Chat 2 does not promote R17. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_16DAA16126896ADC855E`.
