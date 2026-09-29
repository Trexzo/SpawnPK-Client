# Chat 2 — achievement and daily challenge interfaces R380

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/a` -> `CLIENT_CLASS_000573` -> `AchievementDiaryInterface`
- `rs/n/c/b` -> `CLIENT_CLASS_000632` -> `DailyChallengesInterface`
- review: `SEMREVIEW_569FE1B63308240CFE05`

## AchievementDiaryInterface

Exact v308 preserves the title:

`@or1@SpawnPK Achievement Diary`

and a complete achievement interface surface:

- Completed (0/100)
- Title of the achievement
- Progress
- Bonuses you'll receive
- Items you'll receive
- Select achievement
- Collect reward
- Collect all rewards
- achievements/SPRITE resources.

## DailyChallengesInterface

Exact v308 preserves:

`<img=217> <u=16754944>Daily Challenges`

plus:

- challenge rows and progress bars;
- Collect reward;
- View information;
- `You don't have any challenges!`;
- exact sample challenge placeholders such as `Deep wild pking` and
  `Kill 50 players in\nlevel 30+ wild`;
- gameframe/tab resources.

The two classes therefore represent distinct achievement-diary and daily-challenge surfaces.

## Boundary

R380 remains non-canonical class-only semantic research. No reward/server logic is inferred.
