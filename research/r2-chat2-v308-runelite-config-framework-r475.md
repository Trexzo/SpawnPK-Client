# Chat 2 — exact-v308 RuneLite config framework R475

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R475 recovers the complete top-level `rs/e/a..q` configuration package:

- 000143 `rs/e/a` -> `Alpha`
- 000144 `rs/e/b` -> `Config`
- 000145 `rs/e/c` -> `ConfigData`
- 000146 `rs/e/d` -> `ConfigDescriptor`
- 000147 `rs/e/e` -> `ConfigGroup`
- 000148 `rs/e/f` -> `ConfigInvocationHandler`
- 000149 `rs/e/g` -> `ConfigItem`
- 000150 `rs/e/h` -> `ConfigItemDescriptor`
- 000151 `rs/e/i` -> `ConfigManager`
- 000152 `rs/e/j` -> `ConfigObject`
- 000153 `rs/e/k` -> `ConfigProfile`
- 000154 `rs/e/l` -> `ConfigSection`
- 000155 `rs/e/m` -> `ConfigSectionDescriptor`
- 000156 `rs/e/n` -> `FlashNotification`
- 000157 `rs/e/o` -> `Range`
- 000158 `rs/e/p` -> `RequestFocusType`
- 000159 `rs/e/q` -> `Units`

Review: `SEMREVIEW_6B9659FB6E943020492F`

## Exact framework joins

`ConfigManager` owns the live Gson/EventBus/config-data stack, creates dynamic proxies for
types extending `Config`, resolves `ConfigGroup` / `ConfigItem` annotations, applies
defaults, persists profiles and produces `ConfigDescriptor` metadata.

`ConfigInvocationHandler` is the exact Java InvocationHandler backing those proxies.
`ConfigData` is the file-backed String configuration store.
`ConfigDescriptor` aggregates one ConfigGroup plus section/item descriptor collections.
`ConfigItemDescriptor` and `ConfigSectionDescriptor` both implement `ConfigObject`.

## Preserved identities

Several exact-v308 constants make the source lineage unusually strong:

- `ConfigItemDescriptor(item=`
- `ConfigSectionDescriptor(key=`
- `ConfigProfile(id=`
- `Configuration method {} has no @ConfigItem!`
- `Configuration proxy class {} has no @ConfigGroup!`
- `RL configurations`

The annotation contracts and target/retention metadata match RuneLite source directly.

## Enum identities

`FlashNotification` preserves the exact five-value notification enum and display strings.

`RequestFocusType` preserves the historical three-value shape:

- OFF
- REQUEST
- FORCE

Older RuneLite/OpenOSRS lineages expose this exact pre-TASKBAR version; newer RuneLite adds
TASKBAR without changing the class identity.

## Boundary

This batch is class-only, non-canonical semantic research. No fields/methods are proposed and
no source rewrite or canonical acceptance is performed.
