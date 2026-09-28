# Chat 2 — exact-v308 configuration framework semantics R16

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R16 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R15 review batches.

## Deterministic review result

- candidate classes: **13**
- resolved proposals: **13**
- unresolved: **0**
- review ID: `SEMREVIEW_EA07D515D935757E2910`
- field/method proposals: **0**

## Core annotations and marker interface

- `rs/e/a` -> `Alpha`
- `rs/e/b` -> `Config`
- `rs/e/e` -> `ConfigGroup`
- `rs/e/g` -> `ConfigItem`
- `rs/e/l` -> `ConfigSection`
- `rs/e/o` -> `Range`
- `rs/e/q` -> `Units`

Strong exact evidence includes the surviving diagnostics
`Configuration method {} has no @ConfigItem!` and
`Configuration proxy class {} has no @ConfigGroup!`.

`ConfigGroup` is a runtime TYPE annotation with a single group string.
`ConfigItem` is a runtime METHOD annotation carrying position/key/name/description and
section/visibility metadata. `ConfigSection` is a runtime FIELD annotation carrying
section metadata.

The already reviewed `ConfigItemDescriptor` directly exposes `range=...`,
`alpha=...` and `units=...` in its self-identifying toString output, fixing the roles of
`Range`, `Alpha` and `Units`. Units also defines exact constants for milliseconds,
seconds, ticks, minutes, pixels and percent.

The marker interface `Config` is the direct superinterface of reviewed configuration
interfaces including `GpuConfig` and `NotesConfig`.

## Descriptor/proxy/manager framework

- `rs/e/d` -> `ConfigDescriptor`
- `rs/e/f` -> `ConfigInvocationHandler`
- `rs/e/i` -> `ConfigManager`
- `rs/e/j` -> `ConfigObject`

`ConfigDescriptor` aggregates one ConfigGroup plus collections of ConfigSectionDescriptor
and ConfigItemDescriptor objects.

`ConfigInvocationHandler` implements `java.lang.reflect.InvocationHandler` and contains
the exact ConfigGroup/ConfigItem proxy diagnostics, default-method invocation, cache and
unmarshal logic.

`ConfigManager` owns EventBus, ConfigStore and ConfigInvocationHandler, creates dynamic
configuration proxies, builds config descriptors, reads/writes group/key values and handles
profile/default persistence.

`ConfigObject` is the shared String/String/int name-description-position contract
implemented by both ConfigItemDescriptor and ConfigSectionDescriptor.

## Notification configuration enums

- `rs/e/n` -> `FlashNotification`
- `rs/e/p` -> `RequestFocusType`

The notification config binds `flashNotification` directly to `rs/e/n`; that enum has
exact constants:

- `DISABLED`
- `FLASH_TWO_SECONDS`
- `FLASH_UNTIL_CANCELLED`
- `SOLID_TWO_SECONDS`
- `SOLID_UNTIL_CANCELLED`

The `notificationRequestFocus` item has exact title `Request focus` and description
`Configures the window focus request type on notification`, returning `rs/e/p`, whose
constants are `FORCE`, `OFF` and `REQUEST`.

## Acceptance boundary

Chat 2 does not promote R16. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_EA07D515D935757E2910`.
