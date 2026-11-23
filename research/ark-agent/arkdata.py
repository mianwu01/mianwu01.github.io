"""Loaders and small helpers for the datamined Arknights tables.

All functions take the path to `<ArknightsGameData>/zh_CN/gamedata`.
Nothing here talks to the game client; it only reads the public JSON tables.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

NODE_PREFIX = "Torappu.Battle."


def _load(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def buff_templates(gamedata: str) -> dict:
    """battle/buff_template_data.json: buff key -> {eventToActions: {EVENT: [node, ...]}}."""
    return _load(Path(gamedata) / "battle" / "buff_template_data.json")


@lru_cache(maxsize=None)
def character_table(gamedata: str) -> dict:
    return _load(Path(gamedata) / "excel" / "character_table.json")


@lru_cache(maxsize=None)
def stage_table(gamedata: str) -> dict:
    return _load(Path(gamedata) / "excel" / "stage_table.json")["stages"]


@lru_cache(maxsize=None)
def enemy_database(gamedata: str) -> dict:
    """enemy id -> list of per-level entries (level 0 is the base, others are overrides)."""
    raw = _load(Path(gamedata) / "levels" / "enemydata" / "enemy_database.json")
    return {e["Key"]: e["Value"] for e in raw["enemies"]}


def find_stage(gamedata: str, code: str, difficulty: str = "NORMAL") -> dict:
    """Look a stage up by its display code, e.g. 'TL-S-4'. difficulty: NORMAL or FOUR_STAR (突袭)."""
    for stage in stage_table(gamedata).values():
        if stage.get("code") == code and stage.get("difficulty") == difficulty:
            return stage
    raise KeyError(f"stage {code!r} ({difficulty}) not found")


def load_level(gamedata: str, level_id: str) -> dict:
    """level_id as stored in stage_table, e.g. 'Activities/act55side/level_act55side_sub-1-4'."""
    return _load(Path(gamedata) / "levels" / (level_id.lower() + ".json"))


def node_type(node: dict) -> str | None:
    """Short name of an action node, e.g. 'Action.Nodes+CreateBuff'."""
    t = node.get("$type")
    return t.split(",")[0].replace(NODE_PREFIX, "") if t else None


def walk_node_types(obj, acc: set | None = None) -> set:
    """Collect every node type appearing anywhere inside a template (nodes nest)."""
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        t = node_type(obj)
        if t:
            acc.add(t)
        for v in obj.values():
            walk_node_types(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk_node_types(v, acc)
    return acc


def walk_strings(obj, acc: set | None = None) -> set:
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for v in obj.values():
            walk_strings(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk_strings(v, acc)
    elif isinstance(obj, str):
        acc.add(obj)
    return acc


def enemy_attr(entries: list, level: int, key: str):
    """Resolve one attribute of an enemy at a given level (falls back to the base entry)."""
    base = entries[0]["enemyData"]["attributes"][key]
    cur = entries[min(level, len(entries) - 1)]["enemyData"]["attributes"][key]
    return cur["m_value"] if cur.get("m_defined") else base["m_value"]


def enemy_name(entries: list) -> str:
    return entries[0]["enemyData"]["name"]["m_value"]
