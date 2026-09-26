# Chat 2 — exact-v308 key listener dispatch R175

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R175 is a separate non-canonical class-only review for the live client-side key listener
extension and registry/dispatcher.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_8B8C06D161C5FFE9F959`
- field/method proposals: **0**

## Stable IDs

- `rs/g/a/a` -> `CLIENT_CLASS_000177` -> `ClientKeyListener`
- `rs/g/a/b` -> `CLIENT_CLASS_000178` -> `KeyListenerManager`

## ClientKeyListener

`rs/g/a/a` directly extends:

`java.awt.event.KeyListener`

so its core role is exact at the JVM type level.

It also adds one default boolean method that returns false. The exact client does not provide
enough evidence to give that extra hook a narrower semantic name, so R175 deliberately leaves
the hook itself unresolved while recovering the interface-level role.

Multiple live client/plugin classes implement this interface and register through the shared
manager.

## KeyListenerManager

`rs/g/a/b` owns:

`CopyOnWriteArrayList<rs/g/a/a>`

and exposes explicit listener registration/unregistration.

Exact surviving log text includes:

- `Registering key listener: {}`;
- `Unregistered key listener: {}`.

It has three separate KeyEvent dispatch methods covering:

- key pressed;
- key released;
- key typed.

The exact trace/debug text names each path directly:

- `Processing key pressed {} for key listener {}`;
- `Processing key released {} for key listener {}`;
- `Processing key typed {} for key listener {}`;
- corresponding `Consuming key ...` messages.

## Event consumption contract

Before iteration, each dispatch checks whether the incoming AWT KeyEvent is already consumed.

For every registered listener it invokes the corresponding KeyListener callback. If that
listener consumes the KeyEvent, the manager stops dispatching to later listeners.

That makes event consumption an explicit part of the registry's arbitration semantics.

## Base-client integration

The base client `rs/C` forwards its AWT key callbacks to this manager through the live
Launcher/UI graph.

For `keyPressed`:

1. the KeyListenerManager receives the event first;
2. if a registered client listener consumes it, the base client returns immediately;
3. otherwise the legacy key-code/character path continues.

`keyTyped` uses the same front-gate behavior.

`keyReleased` is likewise dispatched through the manager before the existing legacy release
state is updated.

This establishes the class as shared front-of-client key dispatch rather than one plugin's
private listener list.

## Dynamic registrations

Exact live consumers register and unregister ClientKeyListener implementations at subsystem
lifecycle boundaries.

Examples include client overlay/input machinery and plugin modules such as developer-tools
and other RuneLite-style client components.

## Naming boundary

Both names are **0.999**.

`ClientKeyListener` preserves the exact AWT interface role while distinguishing the client
extension from raw Java KeyListener.

`KeyListenerManager` follows the exact registry, dispatch, consumption and lifecycle
behavior. Neither proposal invents a purpose for the interface's extra default boolean hook.

R175 remains class-only.

## Acceptance boundary

Chat 2 does not promote R175. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8B8C06D161C5FFE9F959`.
