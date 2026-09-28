# Chat 2 — R355 duplicate notification-subsystem audit

R355 retains **no semantic proposals**.

The three notification classes were already owned by earlier Chat 2 batches:

- `rs/s/n/a` -> **R9**
- `rs/s/n/b` -> **R9**
- `rs/s/n/c` -> **R14**

Fresh exact-v308 evidence strengthens those reviews:

- config group is literally `notifications`;
- plugin subscribes FocusChanged, ChatMessage and PrivateChatMessage;
- exact alerts include de-aggro, superior slayer/boss and private-message notifications;
- backend posts `NotificationFired`, handles tray/native delivery, beep/audio,
  focus/attention policy, timeout state and screen-flash rendering.

The attempted R355 candidate/review/test artifacts are removed. R355 is
corroboration-only.
