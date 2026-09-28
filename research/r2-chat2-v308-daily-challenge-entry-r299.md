# Chat 2 — exact-v308 Daily Challenge entry R299

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/b$a` -> `CLIENT_CLASS_000633` -> `DailyChallengeEntry`
- review: `SEMREVIEW_735FC1667EB5FF0D064A`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The already-reviewed `DailyChallengesInterface` owns a `List<rs/n/c/b$a>`.

Each record stores:

- challenge name;
- challenge description;
- four integer values supplied together by the parent.

The parent uses the final two integers as current and goal progress, computes a percentage capped at 100%, renders the corresponding progress bar and current/goal/percentage text, and places the entry beside the exact **Collect reward** action.

The challenge name also feeds the same-row information/tooltip path.

## Boundary

R299 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
