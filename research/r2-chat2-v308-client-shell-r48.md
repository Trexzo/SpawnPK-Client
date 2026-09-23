# Chat 2 — exact-v308 client shell semantics R48

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R48 is a separate non-canonical class-only semantic review batch covering the classic
applet/window shell still preserved around the v308 client.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_48C0EF3660A50E61972B`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/C` -> `CLIENT_CLASS_000028`
- `rs/E` -> `CLIENT_CLASS_000032`

## `rs/C` -> `RSApplet`

Exact v308 `rs/Client` extends `rs/C` directly.

`rs/C` itself:

- extends `java.applet.Applet`;
- implements `Runnable`;
- implements component, focus, keyboard, mouse, mouse-motion, mouse-wheel and window
  listeners;
- owns the desktop frame and Graphics state;
- owns client-loop timing/input state;
- implements the applet lifecycle `start`, `stop`, `destroy`;
- implements `update` and `paint`;
- starts and drives the client thread/game loop.

This is the exact classic `RSApplet` / game-shell inheritance role. Public classic source
shows the same Applet + event-listener + game-loop base inherited by Client.

## `rs/E` -> `RSFrame`

`rs/E` is the paired desktop wrapper:

- extends Swing `JFrame`;
- owns exactly one `rs/C` / RSApplet reference;
- creates the visible Jagex top-level window;
- sizes the window around the client surface;
- delegates `update(Graphics)` and `paint(Graphics)` to the applet after the JFrame
  superclass call;
- applies desktop cursor behavior.

Classic clients use the same `RSFrame` role around `RSApplet`; older sources use AWT
`Frame`, while v308 has migrated that wrapper to Swing `JFrame`.

## Naming boundary

The names reflect exact historical/semantic lineage. The public classic source is
corroborating evidence only; v308 bytecode remains authoritative.

## Acceptance boundary

Chat 2 does not promote R48. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_48C0EF3660A50E61972B`.
