# V1.070KR replay adapter

Reference projects inspected: 태조왕건 `native/engine.cpp`, `src/engine.py`, `src/replay_store.py`; 삼국지천명2 `src/ReplayEngine.cs`, `tools/replay_engine.py`, `tools/replay_archive.py`, `tools/add_replay_initial_save_probe.py`. Their addresses and executable hashes were not reused.

## Native boundaries

- `46C5A0`: battle attempt, before and after state. Calls which change no checked state and consume no commands are omitted.
- `4353A1`: a received packet has passed native timestamp eligibility; capture the 104-byte packet and the actual player queue index. This includes slots 0–7, not only local UI input.
- `435356`: playback replaces all eight consumed-command queues. Full generation handles and native per-player order are preserved. Offline timestamp latency is normalized to one tick.
- `46C69C`, `46C6A9`: preserve recorded dispatch availability and wall-clock gate outcomes. Playback pacing is separate from deterministic outcomes.
- `48D330`/`48D6F0`: native initial save/full load. `48D170` redirects only the adapter's private operation to a session file. User save slots are not overwritten. Preserve the save notification queue around checkpoint creation.
- `470CD1`: bootstrap from initialized menu state 9 or 220, use full loader and native battle graphics entry `46AFD0`, then enter battle state 3. Seal on leaving the battle.
- `435040`: suppress live player commands during playback. Recognize the original entry or the existing verified HD mass-selection trampoline before patching it.

State diagnostics: native tick, RNG seed, unit count, FNV-1a over stable unit identity/type/owner/HP/current+pending orders/position/rally coordinates, and all eight players' resources/population fields. This is a diagnostic checksum, not exhaustive equality. Before/after mismatches stop playback; the adapter does not overwrite RNG to conceal a mismatch.

## File and lifecycle

`MYTHRP01` trace: magic, then tag 1 + 40-byte before/after/result/count header + count × (player uint32 + packet[104]); final uint32 FFFFFFFF. Maximum 400 commands per attempt, 50 per slot, 20 selected handles per packet. Trace cap 128 MiB.

`.mythreplay`: `MYTHPK01`, three length-prefixed data records: bounded JSON identity, native checkpoint (up to 32 MiB), sealed trace (up to 128 MiB). SHA-256 of payloads, original game, patched executable, embedded engine; strict field sizes, command/player/handle limits and frame continuity; no executables in archives. Atomic publication only after a second full validation. Session files are retained on failure.

The launcher embeds the x86 DLL and extracts it to a content-addressed cache, then attaches before a battle. Native hook installation validates the baseline and rolls back edits if installation fails. A separate `--replay-watch` process seals/publishes the archive even if the launcher closes first. Replay monitor mode does not take the launcher singleton mutex.

## Verification performed 2026-11-15

1. Actual captured match: 26 consumed commands (movement, harvest, rally, production), 797 retained frames, ticks 0–771. Native full restore and every recorded before/after state passed. Initial unfiltered attempt recording exposed idle timer calls, then an independent playback exposed the wall-clock gate; both were fixed and retested.
2. Extended state check including resources: a test-only engine build starts from a native checkpoint and submits one native diplomacy packet for each of slots 0–7. Captured 8 packets, 1,081 retained frames, ticks 0–1,080. The production engine (without the fixture injector) replayed all frames to COMPLETE without mismatch.
3. A second live playback of that trace passed pause (no tick change), single-step (exactly one tick), resume, 8× speed and COMPLETE at tick 1,080. Menu autoload required no manual match setup.
4. C++ x86 fixture tests execute the actual capture/injection/checksum/parser functions: eight slots, 50-packet boundary, invalid slot/overflow rejection, generation handle retention, truncated input rejection. C# archive tests cover all eight slots, round trip, exact extraction, missing seal, invalid player/selection count, modified payload, extra bytes and oversized metadata.

Not verified: two separate PCs connected in a real network match, disconnect/rejoin, long-running multiplayer, or every campaign script. Multiplayer support is an experimental implementation; the eight-slot integration test is not a claim of two-PC network verification. No broad game balance or existing resolution patches are changed.

## Observer correction 0.6.6

Terrain visibility alone does not expose cached hidden units. `4069B0` checks unit `+1C` before drawing, then suppresses repeated draws using `+60`. Around `46BE00`, active registry entries with positive HP and in-world byte `+324 == 1` temporarily receive visible=1 and previous-tick draw stamp; both fields are restored before simulation resumes. This includes enemy units without exposing embarked/dead units.

`433560` is the shared positional sound queue, not just UI notifications. Its previous unconditional return muted combat effects. A native entry filter now suppresses only events with both map coordinates zero and forwards positional effects to the unmodified queue. Portrait renderers remain suppressed.

Resource text is composed in a top-down 32-bit DIB and committed with one BitBlt/ReleaseDC, after background/unit/selection stages and before final presentation. Non-antialiased Korean font avoids repeated blended glyph accumulation and 8-bit palette dithering. Tests verify complete/stable repeated panel commits and preservation of unrelated terrain pixels.

Actual 6,880-frame, tick 6,507 recording replayed to COMPLETE with state agreement: diagnostic counters recorded P1 13,595 and P2 48,553 successful unit draws, 4,785 positional sound queue forwards. Sound routing was verified in the executable; physical speaker output was not independently measured. The deterministic snapshot remains a diagnostic subset, not exhaustive memory equality. An optional session `diagnostics.enabled` file enables per-second `observer-diagnostics.txt` counts.
