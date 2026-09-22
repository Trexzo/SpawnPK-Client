# R2 Chat 2 — member remap proposal handoff

R2B explicitly leaves member names unchanged. Chat 2 therefore emits a separate,
non-executable proposal document for R2C rather than modifying the class remap plan.

The proposal key is:

```text
stable owner logical ID
+ exact source member name
+ exact source descriptor
-> proposed English member name
```

This lets the integration lane independently verify that a proposal still refers to the
exact member in the exact build before any ASM member remapping is authorized.

## v308 seed

Owner `CLIENT_CLASS_000030` / `rs/Client`:

- `a(J)V -> addFriend`
- `f(J)V -> removeFriend`
- `h(J)V -> addIgnore`
- `i(J)V -> removeIgnore`
- `P:I -> loginRewardContainerIndex`

Owner `CLIENT_CLASS_000299` / `rs/i/b`:

- `f:Lrs/l/F; -> adventureOrbSprite`
- `g:Lrs/l/F; -> adventureOrbHoverSprite`

All seven remain research proposals. Nothing in Chat 2's output is an executable R2C
member-remap plan or an assertion that the proposed names were the original developer
identifiers.
