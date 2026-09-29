# Chat 2 — exact-v308 native input prompts R402

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j/a/b` -> `CLIENT_CLASS_000303` -> `NativeInputPromptManager`
- `rs/j/a/d` -> `CLIENT_CLASS_000305` -> `NativeInputPrompt`
- `rs/j/a/d$a` -> `CLIENT_CLASS_000306` -> `NativeInputPromptMode`
- review: `SEMREVIEW_15BFA0D32C13859FA743`

## Prompt manager

The manager owns the live Client and exactly one current prompt. Its factory creates a new
prompt, stores it as current, and its completion path validates/submits that prompt before
clearing the slot.

## Prompt model

The prompt stores:

- prompt label;
- current value;
- optional prefix/suffix;
- mode;
- optional validation predicate;
- optional submission consumer;
- optional font/render references.

Default state is:

- label `Enter text:`
- empty value/prefix/suffix
- mode `TEXT`

Activation copies the configured value into Client's native input buffer and enables the
client's input mode.

## Prompt modes

The nested enum preserves the exact constants:

- `TEXT`
- `AMOUNT`
- `USERNAME`

## Withheld siblings

`rs/j/a/a` is an empty lifecycle base and `rs/j/a/c` is an empty helper/container.
Neither has enough recoverable behavior for a meaningful semantic name, so they remain
unnamed.

R402 remains non-canonical semantic research only.
