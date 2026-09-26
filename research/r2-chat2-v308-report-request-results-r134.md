# Chat 2 — exact-v308 Report Request Results receiver / ScriptPacket 20 R134

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R134 is a separate non-canonical class-only review for the self-contained Report Request
Results window, its socket receiver and the exact ScriptPacket start/stop controller.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_ED00F196692ECC124E36`
- field/method proposals: **0**

## Stable IDs

- `rs/q/b/a` -> `CLIENT_CLASS_000764` -> `ReportRequestResultsWindow`
- `rs/q/b/d` -> `CLIENT_CLASS_000767` -> `ReportRequestResultsReceiver`
- `rs/q/b/e` -> `CLIENT_CLASS_000768`
  -> `ReportRequestResultsPacketHandler`

## ReportRequestResultsWindow

`rs/q/b/a` extends `JFrame` and preserves the exact title:

`Report Request Results`

Its main text area starts with:

`Waiting for results..`

The window is an 800x600 results viewer centered relative to the SpawnPK Launcher frame.

It also owns a searchable result surface:

- exact dialog title `Find Text`;
- exact label `Find:`;
- exact status `Match results: N/A`;
- Ctrl+F opens the find dialog;
- arrow/page keys navigate matching text.

The receiver queue-drain helper `rs/q/b/f` lazily creates this exact window and appends
every queued receiver String into its JTextArea.

## ReportRequestResultsReceiver

`rs/q/b/d` implements `Runnable` and owns an AtomicBoolean lifecycle.

Exact receiver diagnostics include:

- `Receiver thread started!`;
- `Connected to the server!`;
- `Receiver has stopped!`.

It opens a Socket to the configured SpawnPK host `rs/f/a.j` on port **2456** and reads
UTF messages.

Its exact protocol vocabulary includes:

- `Login`;
- `Login request @`;
- `Logout`;
- `Unregistered (logout)`;
- `Could`;
- `END`.

Parsed messages are queued. A Swing Timer schedules `rs/q/b/f`, which drains that queue
directly into the exact `Report Request Results` window.

The receiver formats packet/server timestamp values through a
`yyyy-MM-dd hh:mm:ss a` formatter before display.

The exact dependency graph is tight: outside its rs/q/b helper classes, the live external
reference is the ScriptPacket dispatcher registration path.

## ScriptPacket 20

R115 registers ScriptPacket **20** from `rs/q/b/d.b`.

Exact v308 initializes that field with:

`new rs/q/b/e()`

The complete handler surface is:

- selector **0** -> stop `rs/q/b/d.a`;
- selector **1** -> start `rs/q/b/d.a`.

There are no other selector branches and no second subsystem mutation.

## Naming boundary

`ReportRequestResultsWindow` follows an exact surviving JFrame title and is **0.999**.

`ReportRequestResultsReceiver` is **0.998**: its receiver/socket behavior and exclusive
result-window sink are exact, while the original source class noun is stripped.

`ReportRequestResultsPacketHandler` is **0.999** because exact ScriptPacket registration
and the complete start/stop surface bind it directly to that receiver.

R134 remains class-only.

## Acceptance boundary

Chat 2 does not promote R134. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_ED00F196692ECC124E36`.
