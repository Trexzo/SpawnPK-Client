# Chat 2 — exact-v308 login background glitch animator R310

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b` -> `CLIENT_CLASS_000366` -> `LoginBackgroundGlitchAnimator`
- review: `SEMREVIEW_47ADE33AC01781F97320`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

`LoginScreen` is the sole exact-v308 construction site. It creates this object from `/assets/bg` and `/assets/bg 2` with displacement magnitude **6**, stores it as login-screen state, and invokes its draw method from the login rendering path.

The animator always draws the base background. Its secondary background enters a randomized horizontal displacement cycle, advances every **45 ms** to the configured magnitude, then steps back to zero before becoming idle again.

That caller/resource ownership is strong enough to use the domain-specific role `LoginBackgroundGlitchAnimator`; the underlying motion primitive itself remains generic implementation detail.

## Boundary

R310 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
