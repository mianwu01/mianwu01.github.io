# ark-agent: first measurements on the datamined Arknights tables

Exploratory scripts for the question "how much of the game's behaviour logic is visible in
the public datamined tables, and how much of it does one concrete clear depend on?".
They only read the public JSON tables; nothing here touches the game client.

This folder lives in the website repository only because that is where the session ran.
It is self-contained and should move to its own repository.

## Data

Public repository `Kengxxiao/ArknightsGameData` (CN server). The numbers below are from commit
`7e56005` (2026-11-16, client 2.7.91). A sparse clone is enough:

```bash
git clone --depth 300 --filter=blob:none --sparse https://github.com/Kengxxiao/ArknightsGameData
cd ArknightsGameData
git sparse-checkout set --skip-checks zh_CN/gamedata/excel zh_CN/gamedata/battle zh_CN/gamedata/levels
```

`--depth 300` reaches back to January 2023, which the `history` command needs.

## Scripts

```bash
GD=/path/to/ArknightsGameData/zh_CN/gamedata

python dsl_census.py census  $GD                        # size and tail of the behaviour DSL
python dsl_census.py history $GD --out history.json     # growth of node types over data versions
python dsl_census.py cone    $GD --stage TL-S-4 --ops 望 结城理 --history history.json
python stage_timeline.py     $GD TL-S-4 --hard          # map, runes, enemies, spawn schedule
```

## What the data contains

Buff behaviour is data, not code. `battle/buff_template_data.json` maps each buff key to
`eventToActions`: for each event (`ON_TAKE_DAMAGE`, `ON_BUFF_START`, ...) a list of action
nodes (`CreateBuff`, `IfElse`, `AdvancedApplyDamage`, ...), each with its parameters. The
node implementations are in the client binary, so the node types are the unit of hidden
semantics. Level files give the map, routes, spawn schedule, runes and the random seed.

Not in the tables: the core loop (movement, targeting, blocking, attack timing) and
behaviour written as client-side ability classes, which the tables reference only by name
(for example the enemy skill `ThrowSoil`). The Lua folder is UI code and hot-fix patches.

## Measurements (2026-11-16 data)

| Quantity | Value |
|---|---|
| Buff templates | 9,181 |
| Action nodes in total | 44,045 |
| Distinct node types | 1,473 |
| Distinct events | 106 |
| Node types covering 82% of all nodes | 100 |
| Node types used exactly once | 460 |
| Node types per operator, median / 6-star median / max | 8 / 22 / 67 |
| Operators with no buff template | 87 of 468 |
| Node types, 2023-12-05 to 2026-11-16 | 570 to 1,473 (25.5 new per month) |
| Update carrying the TL event (2026-10-09 to 2026-11-01) | +392 templates, +55 node types |

Dependency cone of one concrete clear, TL-S-4 with 望 and 结城理:

| Part | Templates | Node types |
|---|---|---|
| Stage TL-S-4 (enemies, traps, event buffs) | 27 | 39 |
| 望 | 20 | 25 |
| 结城理 | 36 | 57 |
| Union | 81 | 97 (6.6% of all) |
| Union without 结城理 (the single-operator clear) | 46 | 56 (3.8% of all) |

Of the 97 node types, 6 first appeared in the update that shipped the event (five
`Act55Side*` nodes, one of them camera-only, plus `SetEnemyPathCostProfile`); 64 already
existed in December 2023.

Enemy skills are a second, fully hidden layer: 850 of 2,234 enemies carry at least one
skill, referenced by 762 distinct ability names with no behaviour in the tables.

## Caveats

- Template ownership is inferred from key prefixes (`wang_s_3` belongs to `char_2027_wang`,
  `enemy_blksnk[s3]` to `enemy_1602_blksnk2`). Behaviour in ability classes or the core loop
  is not counted, so cone sizes are lower bounds. The two bosses of TL-S-4 list no skills in
  the enemy table at all: when they cast is decided in client code.
- History is sampled at every third data version, so "first seen" dates are accurate to
  within about a month.
- The spawn schedule uses the documented reading of the wave format and has not been
  checked against the real client.
