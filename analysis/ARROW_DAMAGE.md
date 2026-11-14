# V1.070KR arrow damage verification

Source: original MMyth.exe SHA256 `1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf`.
No balance patches were applied during this investigation.

Version 0.5.5 subsequently changes fire-arrow class 3 to the native 2× branch at 00401468. The findings below describe the original game. Pass a recipe path as the probe's third argument to verify the changed version; its expected fire multiplier includes class 3. All three launcher recipes are verified this way.

## Mapping

- 00403474–004037A7: archer attack dispatch reads player's arrow selection at B137CC. Selection 2 creates projectile 4 (00403744), selection 3 creates projectile 5 (004037A0).
- 00456BDC jump table: projectile 4 → 00457780 → attack kind 17; projectile 5 → 004577D0 → attack kind 38.
- Original full hit pipeline: 00401640 → 00401DE0 → 004010E0; HP subtraction at 00464BE0.

## Formula

Let A be the effective attack delivered by the projectile, including the attacker's health-dependent attack and bonuses. Let D be the target's effective defence, capped at 90 in these two attack branches.

`C = A × multiplier`

`damage = max(1, C - floor(C × min(D,90) / 100))`

Fire multiplier: 2 for internal defence classes 5 and 6, otherwise 1.
Poison multiplier: 2 for classes 1, 2 and 4, otherwise 1.
Runtime template classification: classes 1/2/4 contain biological units; class 3 contains siege engines and ships; class 6 contains buildings. No named standard template of class 5 was present in the inspected template set.

## Continuing damage

The arrow impact callbacks invoke the immediate damage pipeline; they do not install a burning/poison status, schedule subsequent HP loss or create a damaging status object. Running the complete projectile impact dispatcher for projectile 4 and projectile 5 changed only the target's HP bytes in the fixture. The alive-target impact pipeline has no type-17/type-38 continuing-effect branch. Visual trail effects are not a continuing damage timer on the target.

Therefore damage-over-time from a single fire/poison arrow is 0 HP and its damaging status duration is 0 simulation ticks (0 seconds). This is distinct from the duration of cosmetic effects and from repeat shots.

## Test evidence

`arrow_damage_probe.py` maps the original executable into Unicorn and executes its original x86 functions. It checks 16,968 combinations: 14 attack values, defence 0–100, six defence classes, both attack kinds. It also invokes the original immediate hit routine and the full projectile hit dispatcher. A=100, D=30, class 1 yields fire 70 HP and poison 140 HP, with no target fields changed outside HP.

Commands and output are reproducible with the original game executable; results are in `arrow-damage-results.txt`. These are code-execution tests, not a stopwatch measurement of a live multiplayer match.
