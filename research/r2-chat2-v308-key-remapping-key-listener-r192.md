# Chat 2 — exact-v308 Key Remapping key listener R192

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R192 is a separate non-canonical class-only review for the key-listener implementation owned
by the already-reviewed Key Remapping plugin.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_A2A2D557F097BBEE9A6F`
- field/method proposals: **0**

## Stable ID

`rs/s/j/b` -> `CLIENT_CLASS_000923` -> `KeyRemappingKeyListener`

## Existing package authority

Earlier reviews recover:

- `rs/s/j/a` -> `KeyRemappingConfig`;
- `rs/s/j/c` -> `KeyRemappingPlugin`.

The config covers camera remapping and replacement bindings for the function keys.

## Exact registration

`KeyRemappingPlugin` owns one `rs/s/j/b` instance and one client key-listener manager.

Plugin startup registers that exact listener.
Plugin shutdown unregisters it.

The target class implements the client key-listener interface and exposes the three normal
keyboard callbacks:

- `keyTyped`;
- `keyPressed`;
- `keyReleased`.

## Exact camera remapping

When camera remapping is enabled, the listener compares the pressed event against the four
configured directional keybinds.

Matching inputs are rewritten to the standard arrow-key codes:

- up;
- down;
- left;
- right.

The original key code is retained in the listener's remap table so release events can be
rewritten consistently.

## Exact F-key remapping

When F-key remapping is enabled, the configured replacement bindings are mapped to F1 through
F12.

For a remapped press the listener:

- stores the original key code -> replacement key code mapping;
- rewrites the KeyEvent key code;
- suppresses the original typed character when needed;
- tracks suppressed characters so the corresponding keyTyped event is consumed.

On key release it removes the saved mapping and writes the same replacement key code back to
the release event.

That gives one coherent press/typed/release remapping lifecycle.

## Plugin chat-key path

The listener also owns the Key Remapping plugin's keyboard path for its chat state.

The reviewed plugin exposes the exact text:

`Press Enter to Chat...`

and owns the state transitions used by the listener.

The listener handles the matching Enter/Escape/Backspace path and slash/semicolon text-entry
cases through that same plugin state. This behavior is why the proposal is named for the
listener's structural owner rather than a narrower `KeyCodeRemapper` noun.

## Naming boundary

`KeyRemappingKeyListener` is **0.999**.

The name is descriptive: exact v308 proves exclusive KeyRemappingPlugin registration and a
complete key-listener responsibility combining configured remapping with that plugin's chat
keyboard state. It is not claimed as the stripped original developer identifier.

R192 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R192. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A2A2D557F097BBEE9A6F`.
