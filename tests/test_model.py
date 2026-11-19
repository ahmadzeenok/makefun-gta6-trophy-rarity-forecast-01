"""Tests for main.py (run: python3 tests/test_model.py).

Checks, on the kit's practice cases and on a synthetic final-like case
(launch night + a live read, target 2026-11-26):
  - the output is valid (55 rows, 5 non-decreasing quantiles, 0-100);
  - two runs write byte-identical output;
  - it runs in well under the 8-second cap;
  - the headline medians are in the ranges the write-up argues for
    (Chapter 1 highest of the story trophies, platinum a fraction of a
    percent, "Just Like Paradise" ~100%).
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT_INPUT = ROOT.parent / "kit" / "gta6-trophy-rarity-forecast-01-kit" / "input"


def run(inp: Path, out: Path) -> float:
    env = dict(os.environ)
    env["MAKEFUN_INPUT_DIR"] = str(inp)
    env["MAKEFUN_OUTPUT_DIR"] = str(out)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / "main.py")],
                       env=env, capture_output=True, text=True)
    dt = time.time() - t0
    assert r.returncode == 0, r.stderr
    return dt


def check_valid(out: Path, n_trophies: int = 55):
    outs = sorted(out.glob("*.out"))
    assert outs, "no output files"
    for p in outs:
        d = json.loads(p.read_text())
        assert set(d) == {"trophies"}, p
        assert len(d["trophies"]) == n_trophies, p
        ids = [row["id"] for row in d["trophies"]]
        assert len(set(ids)) == n_trophies, "duplicate trophy id"
        for row in d["trophies"]:
            assert set(row) == {"id", "q"}, row
            q = row["q"]
            assert len(q) == 5, row
            assert all(isinstance(x, (int, float)) and 0 <= x <= 100 for x in q), row
            assert all(q[i] <= q[i + 1] for i in range(4)), row
    return outs


def medians(out: Path):
    d = json.loads(next(iter(sorted(out.glob("*.out")))).read_text())
    return {row["id"]: row["q"][2] for row in d["trophies"]}


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # Practice cases.
        o1, o2 = td / "o1", td / "o2"
        o1.mkdir()
        o2.mkdir()
        dt = run(KIT_INPUT, o1)
        assert dt < 8, f"practice run took {dt}s"
        check_valid(o1)
        run(KIT_INPUT, o2)
        for a, b in zip(sorted(o1.glob("*.out")), sorted(o2.glob("*.out"))):
            assert a.read_bytes() == b.read_bytes(), "not deterministic"
        print(f"practice: valid, deterministic, {dt:.2f}s")

        # Synthetic final-like case.
        synth_in = td / "synth_in"
        synth_in.mkdir()
        subprocess.run([sys.executable, str(ROOT / "tests" / "make_synth_case.py"),
                        str(synth_in)], check=True)
        o3 = td / "o3"
        o3.mkdir()
        dt = run(synth_in, o3)
        assert dt < 8, f"synthetic run took {dt}s"
        check_valid(o3)
        m = medians(o3)
        assert m[3] > m[4] > m[5] > m[6] > m[7], "story chapters should fall off"
        assert 10 < m[3] < 60, f"Chapter 1 median {m[3]} outside 10-60%"
        assert m[1] < 1.0, f"platinum median {m[1]} should be under 1%"
        assert m[14] < 1.0, f"100% completion median {m[14]} should be under 1%"
        assert m[2] > 99.0, "Just Like Paradise should stay ~100%"
        assert m[15] < 2.0 and m[30] < 2.0 and m[31] < 2.0, "grinds stay under 2%"
        print(f"synthetic final: valid, {dt:.2f}s; "
              f"Ch1={m[3]:.1f}% Final={m[7]:.1f}% Plat={m[1]:.2f}%")
    print("all tests passed")


if __name__ == "__main__":
    main()
