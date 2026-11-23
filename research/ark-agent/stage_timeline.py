"""Print a stage's map, enemy roster and spawn schedule straight from the level file.

Usage:
  python stage_timeline.py <gamedata> TL-S-4 [--hard]

Spawn times are computed as wave.preDelay + fragment.preDelay (cumulative, each fragment
lasting as long as its longest action) + action.preDelay + i * action.interval. That is
the documented reading of the format; it has not yet been checked against the real client,
and it ignores actions that wait on kills (blockFragment) or random spawn groups.
"""
from __future__ import annotations

import argparse
from collections import Counter

import arkdata

TILE_SYMBOL = {
    "tile_forbidden": "#", "tile_road": ".", "tile_floor": "_", "tile_wall": "W",
    "tile_start": "S", "tile_end": "E", "tile_flystart": "s", "tile_hole": "O",
    "tile_fence": "F", "tile_fence_bound": "F", "tile_trench": "~",
}


def spawn_schedule(level: dict, hard: bool) -> list[dict]:
    hidden = "normal" if hard else "fstar"  # groups that do NOT appear in this difficulty
    t, out = 0.0, []
    for wi, wave in enumerate(level["waves"]):
        t += wave["preDelay"]
        for fi, frag in enumerate(wave["fragments"]):
            t += frag["preDelay"]
            longest = 0.0
            for act in frag["actions"]:
                longest = max(longest, act["preDelay"] + (act["count"] - 1) * act["interval"])
                if act["actionType"] != "SPAWN" or act.get("hiddenGroup") == hidden:
                    continue
                for i in range(act["count"]):
                    out.append({"t": t + act["preDelay"] + i * act["interval"], "wave": wi,
                                "fragment": fi, "enemy": act["key"], "route": act["routeIndex"]})
            t += longest
        t += wave["postDelay"]
    return sorted(out, key=lambda s: s["t"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gamedata")
    ap.add_argument("code")
    ap.add_argument("--hard", action="store_true", help="challenge mode (突袭)")
    args = ap.parse_args()

    stage = arkdata.find_stage(args.gamedata, args.code, "FOUR_STAR" if args.hard else "NORMAL")
    level = arkdata.load_level(args.gamedata, stage["levelId"])
    opt = level["options"]
    print(f"{stage['code']} {stage['name']} ({stage['difficulty']})  sanity {stage['apCost']}, "
          f"refunded on failure {stage['apFailReturn']}, practice tickets {stage['practiceTicketCost']}")
    print(f"deploy limit {opt['characterLimit']}, life {opt['maxLifePoint']}, initial cost {opt['initialCost']}, "
          f"speed multiplier {opt['moveMultiplier']} tiles/s per unit of move speed, random seed {level['randomSeed']}")

    grid, tiles = level["mapData"]["map"], level["mapData"]["tiles"]
    print("\nmap (as stored; # blocked, . melee tile, ~ trench, _ floor, S start, E exit):")
    for row in grid:
        print("  " + " ".join(TILE_SYMBOL.get(tiles[i]["tileKey"], "?") for i in row))

    print("\nrunes active in this difficulty:")
    mask = "FOUR_STAR" if args.hard else "NORMAL"
    for rune in level.get("runes") or []:
        if rune["difficultyMask"] in ("ALL", mask):
            bb = {b["key"]: (b["valueStr"] if b["valueStr"] is not None else b["value"]) for b in rune["blackboard"]}
            print(f"  {rune['key']}: {bb}")

    db = arkdata.enemy_database(args.gamedata)
    levels = {ref["id"]: ref["level"] for ref in level["enemyDbRefs"]}
    schedule = spawn_schedule(level, args.hard)
    counts = Counter(s["enemy"] for s in schedule)
    print("\nenemies (base stats before runes):")
    for eid, n in counts.most_common():
        e, lv = db[eid], levels.get(eid, 0)
        a = lambda k: arkdata.enemy_attr(e, lv, k)
        print(f"  {n:3d} x {arkdata.enemy_name(e)}  hp {a('maxHp')} atk {a('atk')} def {a('def')} "
              f"res {a('magicResistance')} speed {a('moveSpeed')} interval {a('baseAttackTime')}s weight {a('massLevel')}")

    print(f"\nspawn schedule ({len(schedule)} spawns, last at {schedule[-1]['t']:.1f}s):")
    for s in schedule:
        print(f"  t={s['t']:6.1f}s  route {s['route']:2d}  {arkdata.enemy_name(db[s['enemy']])}")


if __name__ == "__main__":
    main()
