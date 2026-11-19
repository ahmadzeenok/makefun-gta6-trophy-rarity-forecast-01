"""gta6-trophy-rarity-forecast-01: forecast every GTA VI (PS5) trophy's earn rate
on Exophase at a case's target, as five quantiles (5/25/50/75/95%), from the
house's recorded reads of the trophy page in the case's history.

Model (cohort maturity + data-driven trend, blended by horizon)
--------------------------------------------------------------
An Exophase earn rate is earners / players-tracked. Both move fast in launch
week, and in opposite directions at first: the tracked population explodes as
the game rolls out across time zones (638 players at launch night, ~3,870
twelve hours later), so rates are *diluted* even while more players earn each
trophy. Later the population's growth slows and the earners catch up, so rates
recover toward their long-run level. A persistence forecast ("rates stay put")
and a straight trend extrapolation both miss this: persistence ignores the
recovery, a trend fitted to the dilution phase extrapolates a fall that never
comes. This program models the two moving parts separately.

1. Players tracked, N(t).  A log-logistic in log(1 + t) (t = hours since
   2026-11-19T00:00:00Z, the game's launch): N(t) = N_inf / (1 + exp(-(ln(1+t)
   - a) / b)). It rises steeply through the launch, then saturates. Fitted to
   the case's distinct reads by least squares on log N (grid search over a, b;
   N_inf solved in closed form), with a small penalty against absurd
   saturation levels, so the fit stays honest when the history is short.

2. Earners, per trophy.  A cohort model: a player who joins (is first
   tracked) at time s has, by time T, had (T - s) hours to play. The chance
   they have earned trophy i by then is P_i * (1 - exp(-(T - s) / tau_i)),
   where P_i is the trophy's eventual (mature) earn rate and tau_i the wall-
   clock time the average player needs to reach it. The rate at T is then

       rate_i(T) = P_i * [ integral_0^T L'(s) * (1 - exp(-(T - s)/tau_i)) ds ]
                   / L(T)

   with L the fitted N(t)/N_inf curve. This is computed by Simpson's rule.
   P_i and tau_i are priors, set per trophy from its description and tier and
   from the mature rates of the closest analogues (GTA V on Exophase/PSN:
   platinum ~2-4% of players, final mission ~15-34%, online intro ~86-89%;
   see data/analogues.md and README.md). tau_i is the *population-average*
   wall time, deliberately larger than what the first, hardcore, hours suggest:
   the launch-night population is reviewers and New-Zealand players who played
   13 hours straight; the average buyer spreads the same play over days.

3. Data-driven trend.  For each trophy, log(earners) is fitted against
   ln(1 + t) over the distinct reads (least squares, slope clamped), giving a
   second, purely empirical, extrapolation to the target. This is the component
   that listens to the case itself: if the history shows a trophy's earners
   growing faster than the prior expects, the forecast moves with it.

4. Blend.  The two medians are averaged on the logit scale. The weight on the
   data-driven component is 1 / (1 + horizon_days): for a 90-minute practice
   horizon the forecast is essentially the last read (the refresh is
   unpredictable, the expected rate is where it is); for the 4.5-day final
   horizon the cohort model dominates, because a power-law trend extrapolated
   4.5 days is not to be trusted. The special trophy "Just Like Paradise"
   (Complete Gone Fishing) is at 100% in every read; it is forecast to stay
   ~100% (median 99.9%), since a rate that has held at 100% for thousands of
   tracked players is not a sampling artefact.

5. Spread.  Quantiles are the median on the logit scale plus z_tau * spread,
   spread_i = sqrt((0.35 * sqrt(horizon_days))^2 + u_i^2), u_i a per-trophy
   model-uncertainty in logit units (0.6 for early/easy trophies, up to 1.2
   for the platinum and 100% completion). The spread is deliberately honest:
   on the logit scale a factor-of-two miss is ~0.7 units, and the launch-week
   player growth alone makes that the normal case. A forecast that is too
   narrow pays for every trophy outside it; a forecast that is too wide pays
   at every trophy; this spread is the middle of that trade.

Determinism and safety: no randomness, no network, no clock reads (every
time comes from the case file), pure standard library. Any failure inside a
case falls back to the persistence forecast for that case, so the output is
always a valid forecast file. Runs in well under the 8-second cap.

How the grader runs it: `python3 -P -s /bot/main.py` (Python 3.13, standard
library only). Outside the grader, MAKEFUN_INPUT_DIR and MAKEFUN_OUTPUT_DIR
stand in for /input and /output:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# Launch reference: the house trend baseline measures hours from here too.
LAUNCH_EPOCH = "2026-11-19T00:00:00Z"

# ---------------------------------------------------------------------------
# Per-trophy priors.
#
# P   -- the trophy's eventual (mature) earn rate, in percent, among the
#        players Exophase tracks for the game. Anchored on GTA V's mature
#        Exophase rates (PS5: platinum 3.75%, final mission 15.35%; PS4:
#        platinum 2.17%, final mission 33.75%) and on what the description
#        asks for; see data/analogues.md.
# tau -- wall-clock hours the *average* tracked player needs, after first
#        being tracked, to have earned the trophy. Larger than the launch
#        night suggests, because the first readers are the fastest players.
# u   -- model uncertainty for this trophy, in logit units, added in
#        quadrature to the horizon spread (see spread below).
#
# keyed by trophy id; a trophy not listed gets the DEFAULT prior.
# ---------------------------------------------------------------------------
# (P, tau_hours, u)
PRIORS = {
    1: (3.0, 2000, 1.2),    # platinum: Vice Got a Price! (150+ h; ~2 h/day -> ~1800 h wall time)
    2: (99.9, 1, 0.3),      # Just Like Paradise (Gone Fishing) -- see special case
    3: (75.0, 120, 0.6),    # Paradise Lost: Chapter 1
    4: (65.0, 150, 0.6),    # Chapter 2
    5: (55.0, 200, 0.7),    # Chapter 3
    6: (45.0, 250, 0.7),    # Chapter 4
    7: (25.0, 350, 0.8),    # final mission (gold)
    8: (25.0, 250, 0.8),    # Breakfast Run
    9: (25.0, 250, 0.8),    # The Cartel Heist
    10: (25.0, 250, 0.8),   # Child's Play
    11: (25.0, 250, 0.8),   # Headliners
    12: (25.0, 250, 0.8),   # VCIA Takedown
    13: (25.0, 250, 0.8),   # Operation Savage Glory
    14: (1.5, 2000, 1.2),   # 100% Completion (gold; same 150+ h gate as the platinum)
    15: (4.0, 500, 1.0),    # 250 Stunts (silver)
    16: (55.0, 150, 0.7),   # try each activity once
    17: (8.0, 300, 0.9),    # gold in all Shooting Range challenges (silver)
    18: (10.0, 300, 0.9),   # Top Fun Drone Race at every location
    19: (12.0, 300, 0.9),   # win 20 different races
    20: (35.0, 120, 0.7),   # beat Cal in a fishing challenge
    21: (40.0, 120, 0.7),   # complete an arcade game
    22: (20.0, 300, 0.8),   # final mission for Andy
    23: (20.0, 300, 0.8),   # final mission for Kenton
    24: (20.0, 300, 0.8),   # final mission for Billy
    25: (12.0, 350, 0.9),   # 8 stranger mission strands (silver)
    26: (20.0, 300, 0.8),   # final mission for Randy
    27: (20.0, 300, 0.8),   # final mission for Tyrone
    28: (8.0, 350, 1.0),    # meditate at every spot
    29: (15.0, 250, 0.8),   # hunt a unique animal for Bret
    30: (6.0, 500, 1.0),    # 3 Collectible Card sets (silver)
    31: (5.0, 500, 1.0),    # WAiNK It at 100 locations (silver)
    32: (6.0, 500, 1.0),    # complete 50 Challenges
    33: (25.0, 150, 0.8),   # lose a 4-star Wanted Level with your partner
    34: (20.0, 150, 0.8),   # rob 3 shops back-to-back
    35: (25.0, 250, 0.8),   # discover 100 vehicles
    36: (30.0, 96, 0.7),    # 5 enemies in one Combat Focus
    37: (20.0, 200, 0.8),   # unscheduled departure at VCIA
    38: (25.0, 150, 0.8),   # Rhinos
    39: (15.0, 250, 0.8),   # rob a jewelry store undetected
    40: (10.0, 350, 0.9),   # rob 5 Bank Vaults (silver)
    41: (20.0, 200, 0.8),   # rob an Armored Truck
    42: (20.0, 350, 0.9),   # explore all of Leonida
    43: (15.0, 300, 0.9),   # rob an Illegal Operation of each gang
    44: (30.0, 150, 0.8),   # cocktail on Ocean Beach
    45: (25.0, 150, 0.8),   # smash out of a vehicle showroom
    46: (25.0, 150, 0.8),   # bowling at Kolt & Associates
    47: (25.0, 150, 0.8),   # a partnership with mass appeal
    48: (25.0, 150, 0.8),   # choices made
    49: (25.0, 150, 0.8),   # second time's the charm
    50: (20.0, 200, 0.8),   # what the hell just happened?
    51: (25.0, 150, 0.8),   # melee drive-by bowling
    52: (12.0, 350, 0.9),   # launder $250,000 of Marked Bills
    53: (20.0, 250, 0.8),   # spend $100,000 across all shops
    54: (8.0, 400, 1.0),    # purchase all garage properties
    55: (18.0, 250, 0.8),   # register 10 vehicles to Scooter Bros
}
DEFAULT_PRIOR = (20.0, 250, 0.9)

# The horizon (in days) at which the blend is half cohort, half data-driven.
BLEND_HALF_LIFE_DAYS = 1.0
# The data-driven power-law slope is clamped to this range (log earners vs
# ln(1 + t)): earners do not fall over launch week, and they do not grow
# faster than the player base by more than this.
SLOPE_MIN = 0.0
SLOPE_MAX = 2.0


def clamp(x: float) -> float:
    return min(99.99, max(0.01, x))


def logit(pct: float) -> float:
    c = clamp(pct)
    return math.log(c / (100 - c))


def inv_logit(lg: float) -> float:
    if lg >= 0:
        return 100 / (1 + math.exp(-lg))
    e = math.exp(lg)
    return 100 * e / (1 + e)


def round4(x: float):
    """x rounded to 4 decimals, half up, as JavaScript's Math.round does it."""
    scaled = x * 10000
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 10000
    return int(value) if value == int(value) else value


def parse_time(s: str) -> float:
    """ISO-8601 UTC timestamp -> hours since LAUNCH_EPOCH (2026-11-19T00:00Z).

    Times before launch (the first reads are 2026-11-18T23:50Z, New Zealand
    players) come back slightly negative; callers floor at 0 where a log is
    taken. Only the shape matters, and every time comes from the case file.
    """
    # 2026-11-19T03:00:00Z -> days since 2026-11-19, times 24, plus time.
    date_part, time_part = s.split("T")
    y, m, d = (int(v) for v in date_part.split("-"))
    hh, mm, ss = time_part.rstrip("Z").split(":")
    # Days since 2026-11-19, by a fixed day count (no calendar library
    # needed: the cases span 2026-11-18 to 2026-11-26, all in November).
    days = (d - 19) + (30 * (m - 11)) + (365 * (y - 2026))
    hours = days * 24 + int(hh) + int(mm) / 60 + float(ss) / 3600
    return hours


# ---------------------------------------------------------------------------
# Players tracked: log-logistic fit.
# ---------------------------------------------------------------------------

def _logistic_log1p(t: float, a: float, b: float) -> float:
    """L(t) = 1 / (1 + exp(-(ln(1+t) - a) / b)), the share of the eventual
    tracked population that has joined by t hours after launch."""
    x = (math.log1p(max(t, 0.0)) - a) / b
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


def fit_players(epochs):
    """Fit N(t) = N_inf * L(t) to the distinct reads.

    epochs: list of (t_hours, players) with t >= 0, strictly increasing t.
    Returns (N_inf, a, b). Grid search over (a, b); for each, N_inf is the
    least-squares fit in log space. A small penalty keeps N_inf from running
    away when the history is short.
    """
    pts = [(t, n) for (t, n) in epochs if n > 0]
    if not pts:
        return (1.0, 3.0, 0.5)
    if len(pts) == 1:
        return (pts[0][1] * 4.0, math.log1p(pts[0][0]), 0.5)
    t_max = max(t for t, _ in pts)
    n_last = pts[-1][1]
    best = None
    a = 0.0
    while a <= math.log1p(t_max) + 2.0 + 1e-9:
        b = 0.10
        while b <= 1.51:
            # N_inf by least squares on log N: mean(log N_j - log L_j).
            s = 0.0
            ok = True
            for t, n in pts:
                lj = _logistic_log1p(t, a, b)
                if lj <= 1e-9:
                    ok = False
                    break
                s += math.log(n) - math.log(lj)
            if ok:
                n_inf = math.exp(s / len(pts))
                sse = 0.0
                for t, n in pts:
                    pred = n_inf * _logistic_log1p(t, a, b)
                    r = math.log(n) - math.log(max(pred, 1e-9))
                    sse += r * r
                # Penalise saturation far beyond the last read: with only
                # launch-week data the tail is not identified, and an
                # unbounded N_inf would push every cohort rate toward zero.
                over = math.log(max(n_inf / n_last, 1.0))
                if over > math.log(50):
                    sse += 0.05 * (over - math.log(50)) ** 2
                if best is None or sse < best[0]:
                    best = (sse, n_inf, a, b)
            b += 0.05
        a += 0.10
    _, n_inf, a, b = best
    return (n_inf, a, b)


def cohort_rate(prior_p: float, tau: float, target_t: float, n_fit) -> float:
    """The cohort model's rate (percent) at target_t hours after launch.

    rate = P * [ integral_0^T L'(s) (1 - exp(-(T-s)/tau)) ds ] / L(T),
    Simpson's rule, 200 intervals. L is the fitted players-tracked curve.
    """
    n_inf, a, b = n_fit
    lt = _logistic_log1p(target_t, a, b)
    if lt <= 1e-9:
        return prior_p
    n_steps = 200
    h = target_t / n_steps

    def deriv(s: float) -> float:
        # d/ds of L(s): central difference, exact enough at this scale.
        ds = 0.05
        return (_logistic_log1p(s + ds, a, b) - _logistic_log1p(s - ds, a, b)) / (2 * ds)

    total = 0.0
    for k in range(n_steps + 1):
        s = h * k
        w = 1.0 if k in (0, n_steps) else (4.0 if k % 2 == 1 else 2.0)
        total += w * deriv(s) * (1 - math.exp(-(target_t - s) / tau))
    integral = total * h / 3.0
    return prior_p * integral / lt


# ---------------------------------------------------------------------------
# Data-driven component: log(earners) against ln(1 + t).
# ---------------------------------------------------------------------------

def trend_rate(epochs_rates, target_t: float):
    """Extrapolate one trophy's earners by a power law in (1 + t).

    epochs_rates: list of (t_hours, players, rate_percent) for the distinct
    reads, in time order. Returns log(earners at the target), or None when
    the history carries no trend (too few points, or no variation in time).
    """
    pts = []
    for t, n, r in epochs_rates:
        if r is None or r <= 0 or n <= 0:
            continue
        pts.append((t, math.log(max(r * n / 100.0, 1e-6)), math.log1p(max(t, 0.0))))
    if len(pts) < 3:
        return None
    # Least squares of log(earners) on ln(1 + t).
    xs = [p[2] for p in pts]
    ys = [p[1] for p in pts]
    n = len(pts)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 1e-12:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    slope = min(SLOPE_MAX, max(SLOPE_MIN, slope))
    intercept = my - slope * mx
    return intercept + slope * math.log1p(max(target_t, 0.0))


# ---------------------------------------------------------------------------
# One case.
# ---------------------------------------------------------------------------

def forecast_case(case: dict, name: str) -> dict:
    if case.get("levels") != LEVELS:
        raise ValueError(f"{name} asks for levels {case.get('levels')}, not {LEVELS}")
    history = case.get("history") or []
    if not history:
        raise ValueError(f"{name} has no history")
    trophies = case["trophies"]
    horizon_days = case["horizon_minutes"] / 1440.0
    target_t = parse_time(case["target"])

    # Distinct reads: consecutive reads with identical (rates, players) are
    # one Exophase refresh, not new information. Keep the first of each run.
    epochs = []
    prev_key = None
    for read in history:
        rates = read.get("rates") or []
        key = (read.get("players_tracked"), tuple(rates))
        if key == prev_key:
            continue
        prev_key = key
        t = parse_time(read.get("slot") or read.get("at") or case["at"])
        epochs.append((t, read.get("players_tracked") or 0, list(rates)))
    if not epochs:
        epochs = [(parse_time(history[-1].get("slot") or case["at"]),
                   history[-1].get("players_tracked") or 0,
                   list(history[-1].get("rates") or []))]

    last_t, last_n, last_rates = epochs[-1]
    n_fit = fit_players([(t, n) for (t, n, _) in epochs])
    n_target = n_fit[0] * _logistic_log1p(target_t, n_fit[1], n_fit[2])
    # Never forecast fewer tracked players than the last read saw, and never
    # more than 200x it: both are artefacts of a short history, not signal.
    n_target = min(max(n_target, float(last_n)), float(last_n) * 200.0)

    # Weight on the data-driven component: ~1 for an hour's horizon (the
    # last read is the forecast), fading toward the cohort model as the
    # horizon stretches to days.
    w_data = 1.0 / (1.0 + horizon_days / BLEND_HALF_LIFE_DAYS)
    horizon_spread = 0.35 * math.sqrt(horizon_days)

    rows = []
    for i, trophy in enumerate(trophies):
        tid = trophy["id"]
        p_prior, tau, u = PRIORS.get(tid, DEFAULT_PRIOR)
        last = last_rates[i] if i < len(last_rates) else None
        if last is None:
            last = 0.0

        # --- special case: a trophy at 100% in every read stays ~100%. ---
        if last >= 99.9:
            median = 99.9
            spread = 0.3
            rows.append({"id": tid, "q": [round4(inv_logit(logit(median) + z * spread)) for z in Z]})
            continue

        # --- cohort model ---
        med_cohort = cohort_rate(p_prior, tau, target_t, n_fit)

        # --- data-driven trend ---
        series = [(t, n, (rates[i] if i < len(rates) else None)) for (t, n, rates) in epochs]
        log_e = trend_rate(series, target_t)
        if log_e is None:
            med_data = last
        else:
            med_data = 100.0 * math.exp(log_e) / max(n_target, 1.0)

        # --- blend on the logit scale ---
        lg = w_data * logit(med_data) + (1.0 - w_data) * logit(med_cohort)
        median = inv_logit(lg)
        # A trophy cannot be forecast above its eventual rate by much, nor
        # below a tenth of its last read when the history is flat: both are
        # signs the blend, not the game, is moving.
        median = min(median, max(p_prior * 1.05, last))
        median = max(median, min(last, p_prior) * 0.05)

        spread = math.sqrt(horizon_spread * horizon_spread + u * u)
        spread = min(max(spread, 0.5), 2.0)
        rows.append({"id": tid, "q": [round4(inv_logit(logit(median) + z * spread)) for z in Z]})
    return {"trophies": rows}


def persistence_case(case: dict, name: str) -> dict:
    """Fallback: every trophy stays at its last rate, house-baseline spread."""
    history = case.get("history") or []
    last = history[-1] if history else {"rates": []}
    spread = 0.5 * math.sqrt(case["horizon_minutes"] / 1440.0)
    rows = []
    for i, trophy in enumerate(case["trophies"]):
        rate = (last.get("rates") or [None] * len(case["trophies"]))[i]
        lg = logit(rate if rate is not None else 0.0)
        rows.append({"id": trophy["id"],
                     "q": [round4(100 / (1 + math.exp(-(lg + z * spread)))) for z in Z]})
    return {"trophies": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        try:
            forecast = forecast_case(case, path.name)
        except Exception:
            forecast = persistence_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
