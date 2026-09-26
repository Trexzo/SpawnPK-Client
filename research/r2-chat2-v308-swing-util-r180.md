# Chat 2 — exact-v308 SwingUtil source recovery R180

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical source corroboration:

`Jire/tarnish@a4796be8e8cdef2398faf1081fa6a4da8a0190b1 game-client/src/main/java/net/runelite/client/util/SwingUtil.java`

R180 is a separate non-canonical class-only review for `rs/gui/M`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DA004CEB888CF9F43859`
- field/method proposals: **0**

## Stable ID

`rs/gui/M` -> `CLIENT_CLASS_000197` -> `SwingUtil`

## Exact v308 API shape

The class exposes exactly seven public static Swing/UI responsibilities:

1. set sensible Swing UI defaults and system properties;
2. apply a supplied `LookAndFeel`;
3. replace global Swing `FontUIResource` defaults;
4. remove button decorations from an `AbstractButton`;
5. create a Swing `JButton` from `rs/ui/l` plus a callback;
6. attach selected/unselected modal tooltip text;
7. create and install a system `TrayIcon`.

The button factory consumes `rs/ui/l`, already reviewed as `NavigationButton`, including
its icon, tooltip, popup map and callback state.

Exact v308 preserves distinctive implementation strings:

- `jgoodies.popupDropShadowEnabled`
- `sun.awt.noerasebackground`
- `substancelaf.internal.FlatLook`
- `Unable to set look and feel`
- `Unable to add system tray icon`

## Historical RuneLite source match

The pinned historical RuneLite-derived source class is named `SwingUtil` and exposes the
same seven responsibilities with matching source method names:

- `setupDefaults`
- `setLookAndFeel`
- `setFont`
- `createTrayIcon`
- `createSwingButton`
- `removeButtonDecorations`
- `addModalTooltip`

This is a whole-class API/string match, not a name inferred from one literal.

## Provenance boundary

`SwingUtil` is recovered at **0.999**.

The historical source supplies original-name provenance. Exact v308 remains authoritative for
the class identity and runtime behavior.

R180 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R180. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_DA004CEB888CF9F43859`.
