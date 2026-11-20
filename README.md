[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ahmadzeenok/makefun-gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ahmadzeenok/makefun-gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Entry for the [make.fun gta6-trophy-rarity-forecast-01 bounty](https://make.fun/bounty/gta6-trophy-rarity-forecast-01).

# GTA VI trophy rarity forecast — week one (Exophase, PS5)

Entry for make.fun competition `gta6-trophy-rarity-forecast-01`: forecast, for
every trophy of Grand Theft Auto VI on PlayStation 5, the percent of the
players Exophase tracks for the game who will have earned it at
2026-11-26T00:00:00Z (one week after launch), as five quantiles
(5% / 25% / 50% / 75% / 95%). Scored by mean pinball loss on the logit scale.

The graded deliverable is **`main.py`** (Python 3.13, standard library only).
It reads one case file (`/input/<id>.in`, schema
`makefun/gta6-trophies-case/v1`) and writes one forecast file
(`/output/<id>.out`). It runs offline, deterministically, in ~0.1 s.

## The model

An Exophase earn rate is **earners / players-tracked**, and in launch week
both move fast — in opposite directions at first. The tracked population
explodes as the game rolls out across time zones (638 players at launch
night, ~3,870 twelve hours later, from the reads in the kit and a live read
of the page on 2026-11-19 12:32 UTC), so rates are *diluted* even while more
players earn each trophy. Later the population's growth slows and the earners
catch up, so rates recover toward their long-run level. A persistence
forecast ("rates stay put") ignores the recovery; a straight trend fitted to
the dilution phase extrapolates a fall that never comes. This program models
the two moving parts separately:

1. **Players tracked, N(t).** A log-logistic in ln(1 + t), t = hours since
   2026-11-19T00:00:00Z: N(t) = N_inf / (1 + exp(-(ln(1+t) - a) / b)).
   Fitted to the case's distinct reads by least squares on log N (grid search
   over a, b; N_inf solved in closed form), with a small penalty against
   absurd saturation levels.

2. **Earners, per trophy (cohort model).** A player first tracked at time s
   has, by time T, had (T - s) hours to play. The chance they have earned
   trophy i by then is P_i * (1 - exp(-(T - s) / tau_i)), where P_i is the
   trophy's eventual (mature) earn rate and tau_i the wall-clock time the
   *average* player needs to reach it. The rate at T is

   rate_i(T) = P_i * [ ∫_0^T L'(s) (1 - exp(-(T - s)/tau_i)) ds ] / L(T)

   with L the fitted N(t)/N_inf curve (Simpson's rule). P_i and tau_i are
   priors, set per trophy from its description and tier and from the mature
   rates of the closest analogues (see `data/analogues.md`). tau_i is the
   *population-average* wall time, deliberately larger than what the first,
   hardcore, hours suggest: the launch-night population is reviewers and
   New-Zealand players who played 13 hours straight; the average buyer
   spreads the same play over days.

3. **Data-driven trend.** For each trophy, log(earners) is fitted against
   ln(1 + t) over the distinct reads (least squares, slope clamped to
   [0, 2]), giving a purely empirical extrapolation to the target. This is
   the component that listens to the case itself.

4. **Blend.** The two medians are averaged on the logit scale. The weight on
   the data-driven component is 1 / (1 + horizon_days): for a 90-minute
   practice horizon the forecast is essentially the last read (the refresh is
   unpredictable); for the 4.5-day final horizon the cohort model dominates,
   because a power-law trend extrapolated 4.5 days is not to be trusted.
   "Just Like Paradise" (Complete Gone Fishing) is at 100% in every read and
   is forecast to stay ~100% (median 99.9%).

5. **Spread.** Quantiles are the median on the logit scale plus z_tau *
   spread, spread_i = sqrt((0.35 * sqrt(horizon_days))^2 + u_i^2), u_i a
   per-trophy model uncertainty (0.6 for early/easy trophies, up to 1.2 for
   the platinum and 100% completion). On the logit scale a factor-of-two
   miss is ~0.7 units, and the launch-week player growth alone makes that
   the normal case, so the spread is deliberately honest.

Any failure inside a case falls back to the persistence forecast for that
case, so the output is always a valid forecast file.

## What the forecast looks like

`forecast.csv` is the model's forecast for the target 2026-11-26T00:00:00Z,
run on a final-like case built from the launch-night reads plus a live read
of the Exophase page at 2026-11-19 12:32 UTC (see `data/`). The headline
numbers (median, percent of tracked players):

| trophy | median | 90% band |
|---|---|---|
| Chapter 1 (Paradise Lost) | 28.4% | 6.3 – 69.8% |
| Chapter 2 | 19.6% | 4.0 – 58.8% |
| Chapter 3 | 13.7% | 2.4 – 50.6% |
| Chapter 4 | 9.7% | 1.6 – 40.9% |
| Final mission (gold) | 4.5% | 0.7 – 25.2% |
| Platinum | 0.16% | 0.01 – 1.83% |
| 100% completion (gold) | 0.09% | 0.01 – 1.01% |
| Just Like Paradise | 99.9% | 99.84 – 99.94% |

The full per-trophy table (all 55, with absolute player counts) is in
`forecast.csv`. The ordering is the story: early chapters rise fastest,
the final mission and the side strands trail, the grinds (250 stunts,
card sets, WAiNK at 100 locations, 50 challenges) stay under 1%, and the
platinum stays a handful of players out of tens of thousands.

## Sources

- Exophase GTA VI PS5 trophy page,
  https://www.exophase.com/game/grand-theft-auto-vi-psn/trophies/ —
  the house's recorded reads in the kit (`input/p00.in`, `input/p01.in`:
  55 trophies, 638 players tracked, 943 trophies earned at
  2026-11-18T23:50Z) and a live read on 2026-11-19 12:32 UTC (~3,870
  players tracked, ~4,278 trophies earned). `data/launch-night-rates.csv`
  and `data/live-rates-2026-11-19-1232Z.csv`.
- GTA V mature trophy rates on Exophase (PS5: 236,286 players tracked,
  platinum 3.75%, final mission 15.35%; PS4: 784,495 players, platinum
  2.17%, final mission 33.75%) and PSNProfiles (~1.5% platinum) — the
  anchor for the eventual rates P_i. `data/analogues.md`.
- Competition kit (rules, starter, practice cases) for
  `gta6-trophy-rarity-forecast-01`, fetched 2026-11-19.

No data source is fabricated. Every input is either the case file, the
kit's recorded reads, a live read of the public Exophase page, or a cited
mature analogue. Estimates are labelled as such in `main.py` (the PRIORS
table) and here.

## Uncertainty

This is a forecast, not a measurement, and the honest statement is that the
bands are wide. The three largest unknowns, in order:

1. **How many players Exophase will be tracking at the target.** The
   tracked count grew 6x in the first 12 hours; where it lands at day 7
   (tens of thousands, plausibly 12k–130k) moves every rate, because it is
   the denominator. The program fits it from the case's history; a history
   that ends while growth is still rapid leaves it under-identified, and
   the spread is set accordingly.
2. **How fast the average buyer plays.** The launch-night population is
   the fastest players alive; the average buyer spreads the same hours
   over days. tau_i is set for the average buyer, but if the tracked
   population stays unusually engaged, early-story rates land above the
   median; if it goes casual, below.
3. **Exophase's refresh cadence.** The page refreshes every few hours, not
   continuously, so the last read before the deadline may already be
   hours stale, and the answering read at the target is a single refresh.
   A trophy whose true rate sits near a refresh boundary can jump.

The 90% bands in `forecast.csv` are the program's answer to that: they are
wide on purpose, and a trophy whose true rate lands outside its band is
the expected price of a week-one forecast, not a surprise.

## Reproduce

```sh
# practice cases (from the kit)
mkdir -p out
MAKEFUN_INPUT_DIR=../kit/gta6-trophy-rarity-forecast-01-kit/input \
  MAKEFUN_OUTPUT_DIR=out python3 main.py
# synthetic final-like case (launch night + live read, target 2026-11-26)
python3 tests/make_synth_case.py   # writes /tmp/synth_input/f00synth.in
MAKEFUN_INPUT_DIR=/tmp/synth_input MAKEFUN_OUTPUT_DIR=/tmp/synth_out python3 main.py
```

Two runs on the same input write byte-identical output (no randomness, no
clock, no network). `tests/test_model.py` checks the output shape, the
quantile ordering, determinism, and the headline medians.

## License

MIT (see LICENSE).
