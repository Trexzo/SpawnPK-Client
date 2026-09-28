# Chat 2 — exact-v308 MIDI player R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/w/c` -> `CLIENT_CLASS_001111` -> `MidiPlayer`
- proposal: `SEMPROP_480B26EEFCC33331542B`
- review: `SEMREVIEW_D7BF8D68E19752F4C101`

## Exact state

The class owns:

- two String path components;
- `javax.sound.midi.Sequence`;
- `Sequencer`;
- `Synthesizer`;
- volume double.

## Playback lifecycle

Its playback method:

1. joins the configured String path components;
2. stops/closes an existing Sequencer;
3. verifies the target File;
4. loads a MIDI Sequence with `MidiSystem.getSequence`;
5. obtains a non-default Sequencer;
6. assigns the Sequence;
7. opens a Synthesizer;
8. connects the Sequencer transmitter to either the synthesizer receiver or system receiver;
9. opens the Sequencer;
10. installs a MetaEventListener;
11. reapplies stored volume;
12. starts playback.

## Volume

Volume handling has three exact branches:

- synth-as-Mixer: `FloatControl.Type.MASTER_GAIN`;
- synthesizer channels: MIDI controller 7;
- receiver fallback: `ShortMessage` control-change 176 / controller 7 across all 16 channels.

## Live ownership

`rs/v/a` owns the single static `rs/w/c` instance, sets both path Strings and starts it.
That subsystem also changes volume through the same object. Client reaches the player's
public lifecycle path.

## Boundary

This is a media player semantic, not a claim about server-controlled music selection,
region music rules, or original source identifier.

R352 remains non-canonical semantic research only.
