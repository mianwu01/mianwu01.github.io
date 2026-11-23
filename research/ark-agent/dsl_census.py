"""Census of the buff-behaviour DSL in the datamined tables.

Buff behaviour is stored as data: each buff template maps events (ON_TAKE_DAMAGE, ...)
to lists of action nodes (CreateBuff, IfElse, ...). The node implementations live in
the client binary, so the nodes are the unit of "hidden semantics" a simulator must get
right. This script measures:

  census   how many templates / node types / events exist, and how long the tail is
  cone     which templates and node types one stage plus a squad depends on
  history  how fast new node types appear across data versions (needs git history)

Usage:
  python dsl_census.py census  <gamedata>
  python dsl_census.py cone    <gamedata> --stage TL-S-4 --ops 望 结城理 [--history history.json]
  python dsl_census.py history <gamedata> --out history.json [--every 3]

The owner of a template is inferred from its key prefix (e.g. 'wang_s_3' belongs to
char_2027_wang). That is a heuristic: behaviour implemented as client-side ability
classes rather than buff templates is not counted, so cone sizes are lower bounds.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import arkdata

BUFF_PATH = "zh_CN/gamedata/battle/buff_template_data.json"


def build_graph(templates: dict):
    """Per template: node types used, and other templates it references by key."""
    keys = set(templates)
    types = {k: arkdata.walk_node_types(v) for k, v in templates.items()}
    refs = {k: (arkdata.walk_strings(v) & keys) - {k} for k, v in templates.items()}
    return types, refs


def closure(seed: set, refs: dict) -> set:
    seen, stack = set(seed), list(seed)
    while stack:
        for r in refs.get(stack.pop(), ()):
            if r not in seen:
                seen.add(r)
                stack.append(r)
    return seen


def owned_by(templates: dict, prefixes: list[str]) -> set:
    return {k for k in templates if any(k.startswith(p) for p in prefixes)}


def operator_prefixes(char_id: str) -> list[str]:
    short = char_id.split("_", 2)[2]  # char_2027_wang -> wang
    return [short + "_", short + "["]


def stage_prefixes(gamedata: str, level: dict, level_id: str) -> list[str]:
    prefixes = []
    for ref in level["enemyDbRefs"]:
        short = ref["id"].split("_", 2)[2]  # enemy_1602_blksnk2 -> blksnk2
        short = re.sub(r"_\d+$", "", short)  # enemy_10253_dsjxb_2 -> dsjxb (variants share templates)
        prefixes.append("enemy_" + short)
        prefixes.append("enemy_" + re.sub(r"\d+$", "", short))  # blksnk2 shares templates with blksnk
    for inst in (level.get("predefines") or {}).get("tokenInsts", []):
        short = inst["inst"]["characterKey"].split("_", 2)[2]  # trap_347_dsjfye -> dsjfye
        prefixes += ["trap_" + short, short + "_", short + "["]
    prefixes.append(level_id.split("/")[1].lower())  # activity id, e.g. act55side
    return sorted(set(prefixes))


def cmd_census(args):
    templates = arkdata.buff_templates(args.gamedata)
    counts, events, total = Counter(), Counter(), 0

    def count(obj):
        nonlocal total
        if isinstance(obj, dict):
            t = arkdata.node_type(obj)
            if t:
                counts[t] += 1
                total += 1
            for v in obj.values():
                count(v)
        elif isinstance(obj, list):
            for v in obj:
                count(v)

    for tpl in templates.values():
        events.update((tpl.get("eventToActions") or {}).keys())
        count(tpl)
    print(f"templates {len(templates)} | nodes {total} | node types {len(counts)} | events {len(events)}")
    cum = 0
    for i, (_, c) in enumerate(counts.most_common(), 1):
        cum += c
        if i in (10, 25, 50, 100, 200, 400, 800):
            print(f"  top {i:4d} node types cover {cum / total:.1%} of nodes")
    print(f"  node types used exactly once: {sum(1 for c in counts.values() if c == 1)}")
    print("most common node types:")
    for t, c in counts.most_common(args.top):
        print(f"  {c:6d}  {t}")

    types, refs = build_graph(templates)
    per_op = []
    for cid, c in arkdata.character_table(args.gamedata).items():
        if cid.startswith("char_"):
            cone = closure(owned_by(templates, operator_prefixes(cid)), refs)
            per_op.append((c["rarity"], len(set().union(*(types[k] for k in cone)) if cone else set())))
    n = [x[1] for x in per_op]
    six = [x[1] for x in per_op if x[0] == "TIER_6"]
    print(f"operators {len(per_op)}: node types per operator median {statistics.median(n)}, "
          f"max {max(n)}; 6-star median {statistics.median(six)}; "
          f"operators with no template {sum(1 for x in n if x == 0)}")


def cmd_cone(args):
    gd = args.gamedata
    templates = arkdata.buff_templates(gd)
    types, refs = build_graph(templates)
    all_types = set().union(*types.values())

    stage = arkdata.find_stage(gd, args.stage)
    level = arkdata.load_level(gd, stage["levelId"])
    parts = {f"stage {args.stage}": stage_prefixes(gd, level, stage["levelId"])}
    chars = arkdata.character_table(gd)
    for name in args.ops:
        cid = next((k for k, c in chars.items() if c["name"] == name and k.startswith("char_")), None)
        if cid is None:
            raise SystemExit(f"operator {name!r} not found")
        parts[f"operator {name}"] = operator_prefixes(cid)

    first_seen = {}
    if args.history:
        for h in json.load(open(args.history)):
            for t in h["types"]:
                first_seen.setdefault(t, h["date"])

    union_tpl, union_types = set(), set()
    for label, prefixes in parts.items():
        cone = closure(owned_by(templates, prefixes), refs)
        ts = set().union(*(types[k] for k in cone)) if cone else set()
        union_tpl |= cone
        union_types |= ts
        print(f"{label}: {len(cone)} templates, {len(ts)} node types")
    print(f"union: {len(union_tpl)} templates, {len(union_types)} node types "
          f"= {len(union_types) / len(all_types):.1%} of all {len(all_types)} node types")
    if first_seen:
        by_date = Counter(first_seen.get(t, "unknown") for t in union_types)
        print("first appearance of the cone's node types (date of sampled data version):")
        for d, c in sorted(by_date.items()):
            print(f"  {d}: {c}")
        newest = max(d for d in by_date if d != "unknown")
        print(f"node types first seen in the newest version containing them ({newest}):")
        for t in sorted(t for t in union_types if first_seen.get(t) == newest):
            print(f"  {t}")


def cmd_history(args):
    repo = Path(args.gamedata).resolve().parents[1]  # <repo>/zh_CN/gamedata -> <repo>
    log = subprocess.run(["git", "-C", str(repo), "log", "--format=%h %cd", "--date=short", "--", BUFF_PATH],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    commits = [line.split() for line in log if line][::-1]  # oldest first
    picked = commits[::args.every]
    if picked[-1] != commits[-1]:
        picked.append(commits[-1])
    out = []
    for sha, date in picked:
        blob = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{BUFF_PATH}"], capture_output=True)
        if blob.returncode != 0:
            print(f"skip {sha} {date}: {blob.stderr[:80]!r}")
            continue
        templates = json.loads(blob.stdout)
        ts = set()
        for tpl in templates.values():
            arkdata.walk_node_types(tpl, ts)
        out.append({"commit": sha, "date": date, "templates": len(templates), "types": sorted(ts)})
        print(f"{date} {sha} templates {len(templates)} node types {len(ts)}", flush=True)
    json.dump(out, open(args.out, "w"))

    first, last = out[0], out[-1]
    months = (datetime.date.fromisoformat(last["date"]) - datetime.date.fromisoformat(first["date"])).days / 30.44
    grown = len(last["types"]) - len(first["types"])
    print(f"{first['date']} -> {last['date']} ({months:.1f} months): node types "
          f"{len(first['types'])} -> {len(last['types'])}, {grown / months:.1f} new per month; "
          f"templates {first['templates']} -> {last['templates']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("census")
    p.add_argument("gamedata")
    p.add_argument("--top", type=int, default=25)
    p.set_defaults(fn=cmd_census)
    p = sub.add_parser("cone")
    p.add_argument("gamedata")
    p.add_argument("--stage", required=True)
    p.add_argument("--ops", nargs="*", default=[])
    p.add_argument("--history")
    p.set_defaults(fn=cmd_cone)
    p = sub.add_parser("history")
    p.add_argument("gamedata")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=int, default=3)
    p.set_defaults(fn=cmd_history)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
