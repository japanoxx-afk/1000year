# High-resolution rendering optimization — 0.6.13

Verified 2026-11-18 on the hash-locked V1.070KR executable.

## Scope and safety

The HD prototype unconditionally jumped from `47FE99` to the full terrain
clear/redraw at `480553`. That path runs before the native timer gate, so it
also repainted terrain during unsuccessful attempts to advance the same tick.

`scripts/terrain_cache.py` now checks the tick, camera, viewport, map storage,
dimensions, player, daylight/shading inputs, native redraw flags, newly derived
fog-change count, and dirty cells in the visible traversal. Reuse is allowed
only within the same tick with unchanged inputs. Fog derivation remains native;
simulation, unit/effect drawing, command queues and network verification remain
unchanged. Native clip restoration still executes on reuse.

The cache metadata at `.hd+B000` is beyond the selection queue (ending below
`A800`) and before terrain pixels at `.hd+10000`. It is display-only memory.

During redundant waiting, yield for 1ms only when the native deadline has at
least 4ms remaining. The game already requests 1ms timer resolution at `470B6B`.
Do not sleep for redraws or near/after the next native deadline. The native timer
continues to determine when simulation advances.

`native/text_mask.h` caches text rasters by their exact content and positions.
Each presentation still saves/restores its current background and paints glyphs,
so caching does not erase text, preserve old digits, or reintroduce flicker.

## Measured normal-game fixture

`perf-baseline` uses the old 0.6.12 terrain recipe and disables text-mask reuse;
`perf-test` uses the optimized recipe and cached text. Both use the same test
engine, initial save, eight fixture commands, timer and scripted camera moves.
Physical game orders/panning are suppressed in these test builds only.
Measurements cover 1,000 accepted frames. Percentiles include deliberate waits;
process CPU time is used for the overall comparison.

| Metric | Reference | Optimized |
| --- | ---: | ---: |
| Elapsed time | 49,799.647ms | 49,800.359ms |
| Process CPU time | 7,968.750ms | 2,109.375ms |
| Fog/terrain attempts | 555,691 | 54,979 |
| Terrain redraws | 555,691 (forced by old recipe) | 999 |
| Terrain reuses | 0 | 53,980 |
| Timer raster builds | 996 | 50 |
| Timer mean draw cost | 208.729µs | 15.651µs |

CPU time decreased 73.5% in this 1280×720 fixture. This is not an FPS multiplier
or a guarantee for other hardware, battles or settings.

Five 921,600-byte terrain snapshots (ticks 100/300/500/700/900) match byte-for-byte,
including camera moves to opposite map corners. The 1,000-frame traces agree in
tick, RNG, stable unit/resource state, native unit accumulator and network RNG.

## Reproduce

```
python tests/test_terrain_cache.py ORIGINAL_EXE MODULE_DIR hd
python tests/test_terrain_cache.py ORIGINAL_EXE MODULE_DIR wide
python tests/test_resolution_sync.py ORIGINAL_EXE MODULE_DIR
native\build-replay.cmd perf-baseline
native\build-replay.cmd perf-test
python tests/compare_render_perf.py BASELINE_SESSION OPTIMIZED_SESSION
```

Native fixture tests also verify cache hits, changed text invalidation, indexed
pixel application, background restoration and changing surface pitch. Old
HD/wide recipes are retained to restore previously supported replay hashes.
