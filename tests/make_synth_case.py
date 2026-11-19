"""Build a synthetic final-like case for local testing.

History = the kit's launch-night reads plus a live read of the Exophase
page at 2026-11-19 12:32 UTC (rates in LIVE_RATES, players tracked ~3,870,
inferred from the rate granularity and the platinum holding 4 earners).
Checkpoint 2026-11-19T12:30Z, target 2026-11-26T00:00Z (one week after
launch). This is NOT the real final case — the house cuts that at the
deadline — it is a stand-in with the same shape, so the model can be
exercised on a multi-day horizon before submission.

Usage: python3 tests/make_synth_case.py [out_dir]   (default /tmp/synth_input)
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT.parent / "kit" / "gta6-trophy-rarity-forecast-01-kit" / "input"

# Live Exophase rates, 2026-11-19 12:32 UTC, trophy ids 1..55 in order.
LIVE_RATES = [
    0.10, 100.00, 0.49, 0.23, 0.23, 0.23, 0.23, 0.23, 0.23, 0.23,
    0.23, 0.23, 0.23, 0.10, 0.10, 0.13, 0.10, 0.10, 0.13, 1.16,
    0.39, 0.13, 0.13, 0.16, 0.10, 0.10, 0.13, 0.10, 0.13, 0.10,
    0.10, 0.10, 0.18, 0.16, 0.39, 0.13, 0.23, 0.31, 0.18, 0.13,
    0.16, 0.16, 0.13, 0.21, 0.13, 0.16, 0.16, 0.18, 0.16, 0.18,
    0.18, 0.13, 0.18, 0.16, 0.16,
]


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/synth_input")
    out_dir.mkdir(parents=True, exist_ok=True)
    base = json.loads((KIT / "p01.in").read_text())
    case = copy.deepcopy(base)
    case["id"] = "f00synth"
    case["at"] = "2026-11-19T12:30:00Z"
    case["target"] = "2026-11-26T00:00:00Z"
    case["horizon_minutes"] = 9330  # 12:30Z 19 Nov -> 00:00Z 26 Nov
    hist = copy.deepcopy(base["history"])
    hist.append({
        "slot": "2026-11-19T12:30:00Z",
        "at": "2026-11-19T12:32:00Z",
        "players_tracked": 3870,
        "trophies_earned": 4278,
        "rates": LIVE_RATES,
    })
    case["history"] = hist
    (out_dir / "f00synth.in").write_text(json.dumps(case))
    print(f"wrote {out_dir / 'f00synth.in'}")


if __name__ == "__main__":
    main()
