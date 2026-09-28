# Chat 2 — exact-v308 IntegerConfigFormatterFactory R235

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_9BE2027DA0B8605726D5`
- field/method proposals: **0**

## Stable ID

- `rs/s/b/y` -> `CLIENT_CLASS_000885` -> `IntegerConfigFormatterFactory`

## Exact-v308 behavior

The class extends `JFormattedTextField.AbstractFormatterFactory`, owns a
`Map<JFormattedTextField, AbstractFormatter>`, and resolves formatters with
`computeIfAbsent`.

For each field it constructs exact class `rs/s/b/x`, already reviewed in R14 as
`IntegerConfigFormatter`.

That paired formatter:

- obtains the unit string from `rs/e/q`;
- strips the suffix before parsing;
- parses with `Integer.valueOf`;
- converts invalid values into `ParseException`;
- appends the same unit during `valueToString`.

The factory therefore has an exact integer-config formatter-factory role. R235 keeps this
as a descriptive behavior name at confidence **0.997** rather than claiming an original
developer identifier.

## Acceptance boundary

Chat 2 does not promote R235. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_9BE2027DA0B8605726D5`.
