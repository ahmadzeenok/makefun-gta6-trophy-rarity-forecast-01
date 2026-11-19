# Analogues: mature trophy rates used to anchor the eventual rates P_i

The cohort model needs, for each trophy, its *eventual* (mature) earn rate
P_i — the share of the tracked population that will ever earn it. GTA VI has
no mature rates yet (it launched 19 November 2026), so P_i is anchored on
the closest mature analogues, all from public Exophase pages (read
2026-11-19) and PSNProfiles reporting. These are *anchors*, not predictions:
the forecast's day-7 rates are far below them, because only a week of play
has happened; the model's tau_i (wall-clock time for the average player to
reach the trophy) does the work of getting from "eventually" to "by day 7".

## GTA V (the series analogue)

GTA V on PlayStation carries 51 trophies (PS4/PS5 lists: 78 trophies
including GTA Online). Mature Exophase rates:

| trophy | PS5 (236,286 players) | PS4 (784,495 players) |
|---|---|---|
| Platinum ("Los Santos Legend" / "Congratulations! You're Vinewood's biggest star!") | 3.75% | 2.17% |
| Final mission ("Completed the final mission") | 15.35% | 33.75% |
| 70 gold medals ("Solid Gold, Baby!") | 4.54% | 2.86% |
| GTA Online intro ("Complete the Introduction") | 88.83% | 85.94% |
| 30 Platinum Awards (Online) | 53.94% | 40.09% |
| First-person 15 hours | 25.85% | 17.89% |

PSNProfiles reports GTA V's platinum at roughly 1.5% of players. PowerPyx
puts the GTA V platinum at 150+ hours (50–60 single-player, 100+ online).

Sources: https://www.exophase.com/game/grand-theft-auto-v-psn/trophies/
(PS5), https://www.exophase.com/game/grand-theft-auto-v-ps4/trophies/
(PS4). The PS5 story rates are lower than PS4's because the PS5 tracked
population includes many players who only play GTA Online and never finish
the story — a reminder that the denominator (who is tracked) matters as
much as the numerator.

## How P_i was set for GTA VI

- **Platinum (id 1), 100% completion (id 14):** P = 3.0% / 1.5%. GTA V's
  platinum is 2.2–3.8% mature; GTA VI's platinum also gates on 100%
  completion, and the 100% gold sits just below it. These are the only
  trophies whose P is a single-digit percent at maturity.
- **Story chapters (ids 3–6) and final mission (id 7):** P = 75 / 65 / 55 /
  45 / 25%. GTA V's final mission is 15–34% mature; chapters fall off
  toward it. Chapter 1's P is the highest because nearly every player who
  plays at all finishes the opening chapter; the fall to 25% at the final
  mission is the usual story attrition.
- **Side-mission strands (ids 8–13, 22–24, 26–27):** P = 20–25%. Specific
  missions, so below the chapter rates; GTA V's side content sits in the
  same band.
- **Easy early activities (ids 16, 20, 21, 36):** P = 30–55%. Things a
  player does in the first hours (try each activity, beat Cal at fishing,
  complete an arcade game, 5 enemies in one Combat Focus) are earned by a
  large share of everyone who plays.
- **Mid-game activities and exploration (ids 33–35, 37–43, 44–51, 53,
  55):** P = 15–25%. Robberies, wanted-level escapes, discovering
  vehicles, exploring Leonida — most players get to them eventually, few
  in week one.
- **Grinds and collections (ids 15, 17–19, 25, 28–32, 40, 52, 54):**
  P = 4–12%. 250 stunts, gold in every Shooting Range challenge, 20 race
  wins, 8 stranger strands, meditating everywhere, 3 card sets, WAiNK at
  100 locations, 50 challenges, 5 bank vaults, $250k laundered, all garage
  properties — these take dozens of hours of deliberate effort, so their
  mature rates are low, and their day-7 rates lower still.
- **"Just Like Paradise" (id 2, Complete Gone Fishing):** P = 99.9%. It is
  at 100.00% in every read (638 players at launch night, ~3,870 twelve
  hours later), so it is treated as a trophy essentially every tracked
  player holds, not as a rate to model.

## What is NOT used

No launch-week trophy curve for GTA V or RDR2 is used, because none is
publicly available in a form that can be cited — the mature rates above
are the only hard numbers, and the week-one shape comes from the cohort
model and the GTA VI reads themselves. Nothing here is fabricated: where
a number is a judgement (P_i, tau_i), it is labelled a prior in `main.py`.
