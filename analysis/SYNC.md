# Mixed-resolution simulation rules — 0.6.12

Verified 2026-11-18 against V1.070KR source SHA256
`1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf`.

## Reproduced cause and correction

The old portable recipe used by both native 640×480 and scaled 1024×768
installed only path/movie compatibility and the fire-arrow balance edit.
Internal 1024×768 and 1280×720 additionally installed gameplay hooks for
building rally orders, resource harvesting after production, and three spawn
search paths. The same received command therefore had different consequences.

`generate_portable.py` now uses the simulation/input portion of
`game_features.install`, with `rules_only=True`. Native display initialization,
surface sizes, resource layout and local selection UI remain original. HD/wide
generated executable hashes remain unchanged. Existing portable replays select
the preserved old recipe by their recorded patch hash.

The native network verifier at `4882B0` and error handler at `485E50` are not
disabled or modified; the differential test asserts their original bytes.

## Verification

- Actual x86 order receiver: legacy portable leaves rally `(-1,-1)` for the
  ground command; all corrected recipes set `(30,40)`.
- Actual x86 production searches: on the same asymmetric building/map fixture,
  legacy births are `(48,50)` for all four targets; corrected births are
  `(50,47)`, `(50,53)`, `(48,50)`, `(52,50)` for up/down/left/right. All three
  production paths agree across all corrected resolutions. Six worker types
  retain the resource-harvest dispatch.
- Actual game, same recorded initial save and commands: old portable diverges
  at frame 920 / tick 897 (`54f03d0e` instead of `2a272af5` unit/resource hash).
  Corrected 640×480, 1024×768 and 1280×720 each complete all 6,880 frames with
  equal tick, RNG, stable unit/resource hash, native unit accumulator `B2E9A8`,
  and network frame RNG `A6EA60` (native send path `48760B` masks its low 4 bits).
  Final tick 6507, seed 33928, stable state hash `601a4637`, native accumulator
  `090020da`, network frame RNG `00008488`.
- Diagnostic timer attempts with no state change are discarded when comparing
  accepted frames; their state must match the preceding frame.
- Packaged launcher restores the old portable replay recipe and prepares the
  corrected portable recipe. Core/archive/library/native/installer checks pass.

Cross-resolution save loading also exposed a local minimap-origin overflow:
the save retained the recording screen's minimap coordinates. Replay checkpoint
loading now rebinds that UI origin using each executable's native initializer.
This changes no simulated unit/resource state.

These are differential code execution and local real-game replay tests, not a
two-PC LAN session test. Every participant must update to 0.6.12 and start the
game through the updated launcher; mixing old and corrected rules is unsupported.

## Reproduce

```
python tests/test_resolution_sync.py ORIGINAL_EXE MODULE_DIR
python tests/test_features.py ORIGINAL_EXE MODULE_DIR portable
python tests/test_features.py ORIGINAL_EXE MODULE_DIR hd
python tests/test_features.py ORIGINAL_EXE MODULE_DIR wide
native\build-replay.cmd sync-test
python tests/compare_sync_traces.py PORTABLE_SESSION HD_SESSION WIDE_SESSION
```

`sync-test` writes scalar diagnostics only. Game/save assets are not distributed.
