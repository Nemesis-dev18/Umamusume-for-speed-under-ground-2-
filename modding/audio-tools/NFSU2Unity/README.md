# NFSU2Unity (BlackBox)

Recomp of **Need for Speed Underground 2** (PC, v1.2) in C# on **Unity 6000.3.17f1**, 1:1 with the
original and reading the files of the installed game. Code reusable for other games on the EA
BlackBox engine (U1, MW, Carbon) lives in the `BlackBox.*` namespaces.

> No game files are part of the repository. You need your own installed copy
> (`SPEED2.EXE` v1.2, MD5 `6445adbf4e8d64be51e96a69bba168a4`).

"1:1" is measured, not estimated: file formats are validated against every file of the game, and the
simulation is checked **bit for bit** against the original x86 code executed under Unicorn
(`tools/harness`). The full plan is in **[docs/PLAN.md](docs/PLAN.md)**, the formats in
[docs/formats/](docs/formats/) and the reverse-engineering specs in [docs/re/](docs/re/).

## Roadmap (full conversion)

| # | Phase | Scope |
|---|---|---|
| 1 | **Cars** | Geometry, textures, parts database, runtime texture swaps, composite paint, faithful car shader, wheels, animated parts, damage |
| 2 | **Vehicle physics** | Timing, input, tyres, suspension, engine/drivetrain/nitrous, rigid body, aero, `PhysicsMover::Move`; then car–world and car–car collision |
| 3 | **World** | Tracks (`TRACKS\L4RA`): section streaming, scenery, textures, world collision/topology, lights, sky, weather, reflections, dynamic env map |
| 4 | **Racing & AI** | Race events and rules (circuit, sprint, drift, drag, street-X, URL, outrun), checkpoints, AI racers, traffic, free roam |
| 5 | **Presentation** | Cameras, HUD, full audio (engine, shifts, turbo, nitrous, skids, collisions, ambience, music, speech), NIS cut-scenes, particles/effects |
| 6 | **Front end** | FNG menus, garage and customisation (parts, paint, vinyls, decals, performance tuning/dyno), career, SMS, shops, save games, options |
| 7 | **Platform & polish** | Input devices (gamepad, wheel, rebinding), video/audio options, performance, standalone builds |

## Current status

| Area | Status | Verification | Docs |
|---|---|---|---|
| Chunk/TPK/geometry readers, JDLZ/HUFF | ✅ Done | All 146 car files parse (24 014 solids, 2 759 textures) | [formats](docs/formats/) |
| Car parts database + stock parts | ✅ Done | Identical to reference for all 46 cars (3 539 lines) | [car-parts](docs/re/car-parts.md) |
| Car render layout (LODs, markers, wheels, brakes) | ✅ Done (static pose) | Visual; opening animations pending | [car-render-models](docs/re/car-render-models.md) |
| Runtime texture swaps + composite paint | ✅ Done | Swaps identical to reference; stock paint texels match | [car-textures](docs/re/car-textures.md) |
| Car shader (`IDI_CAR_FX`), light materials, lighting | ✅ Done | SH lighting matches emulated game code (~6e-8); rig camera axes confirmed (right, down, forward); cube faces to confirm in game | [car-shading](docs/re/car-shading.md), [light-materials](docs/re/light-materials.md) |
| FP determinism (x87 PC=24) + maths helpers | ✅ Done | Bit-exact goldens; CW `0x007F` measured on real d3d9 | [fp-determinism](docs/re/fp-determinism.md) |
| Wheel / tyre / suspension / steering | ✅ Done | 15 158 cases bit-exact | [port-status-wheel](docs/re/port-status-wheel.md) |
| Engine / drivetrain / nitrous | ✅ Done | 14 900 cases bit-exact | [port-status-engine](docs/re/port-status-engine.md) |
| Rigid body / aerodynamics | ✅ Done | 15 458 cases bit-exact | [port-status-rigidbody](docs/re/port-status-rigidbody.md) |
| Timing, player input, keyboard layer | ✅ Done | All goldens bit-exact (incl. 6 150 keyboard cases) | [port-status-timing-input](docs/re/port-status-timing-input.md), [input-keyboard](docs/re/input-keyboard.md) |
| `PhysicsMover::Move` integration + `VehicleSim` | ✅ Done | Substeps, full Move and 120-frame drives bit-exact (PEUGOT, GTO, TAXI) | [port-status-integration](docs/re/port-status-integration.md) |
| Performance data, upgrades, tuning | 🟡 Partial | Data decoded; stock build ported; upgrade/junkman/tuning pipeline to port | [physics-data](docs/re/physics-data.md) |
| Audio formats and decoders | ✅ Done | 1 511/1 513 ABK, all GIN and SCHl identical to vgmstream; game float decoders | [audio-formats](docs/re/audio-formats.md) |
| Engine sound (AEMS bank + GIN) | ✅ Done | Matches reference model | [audio-engine](docs/re/audio-engine.md), [port-status-audio-engine](docs/re/port-status-audio-engine.md) |
| Car SFX (shifts, turbo, nitrous, skids, road, wind, AI/traffic engines, collisions) | 🟡 Partial | AEMS bank code runs in a C# VM: 28 061 voice/tick lines identical to Unicorn on all 176 banks; game-side logic follows the asm. DMix mixer (levels, 3D) not ported | [port-status-audio-engine](docs/re/port-status-audio-engine.md) |
| In-game camera (4 race views, smoothing, terrain/nitrous wobble, shake, projection) | ✅ Done | 17 scenarios / 1 013 frames + 375 projections bit-exact; camera collision pending | [camera](docs/re/camera.md) |
| Drive demo (flat ground) | ✅ Playable | Ported physics, suspension, engine sound | — |
| City drive (L4RA) | ✅ Playable | Free-roam start marker, streaming around the car, sky dome, dynamic car env map, in-game light rig | [city-drive](docs/re/city-drive.md) |
| Car lights and shadow | ✅ Done | Light flares, headlight projector on the world, grid + hull shadows; flare/shadow goldens 3 500 cases bit-exact | [car-lights-shadow](docs/re/car-lights-shadow.md) |
| World collision (ground + walls), car–car contacts | 🟡 Partial | GetElevation 16 066, GJK simplex 12 000, witness GJK 4 000 cases bit-exact; contact resolution/impulse without goldens; car–car not ported | [world-collision](docs/re/world-collision.md) |
| Tracks / world rendering (L4RA city) | 🟡 Partial | All sections of the 8 regions parse (L4RA: 393 sections, 48 270 instances, counts match FRSWorlsEditor); WORLD shader, streaming viewer. Lights/flares, sky blend, reflections, LOD rule pending | [world](docs/re/world.md) |
| Races, AI, traffic | ⬜ Not started | | |
| HUD, NIS, music, speech | ⬜ Not started | Decoders for music/speech exist | |
| Front end, garage, career, saves | ⬜ Not started | | |

The whole harness currently reports `RESULT: all PC24 golden cases bit-exact` (~71k cases).

## Usage

1. Point to the game: environment variable `BLACKBOX_GAME_DIR` (default `F:\Games\NFSU2`) or the field
   in the **BlackBox > Car Viewer** window.
2. Open the `Unity/` folder in Unity Hub (6000.3.17f1).
   - **Car viewer:** scene `Assets/Scenes/CarViewer.unity` (right-drag orbits, wheel zooms; change
     `carName` on the `CarViewer` component, e.g. `PEUGOT`, `GTO`, `TAXI`), or **BlackBox > Car Viewer**.
   - **Drive demo:** **BlackBox > Create Drive Demo Scene**, then play `Assets/Scenes/DriveDemo.unity`.
     W/S throttle/brake (reverse when stopped), A/D steer, Space handbrake, Left Shift nitrous,
     M manual gearbox, Q/E shift, X exhaust level (engine sound), C camera view, B look back, T force turbo sound, R reset. The default test ground has terrain patches (camera wobble per terrain) and ramps.
   - **World viewer:** **BlackBox > Create World Viewer Scene**, then play `Assets/Scenes/WorldViewer.unity`.
     WASD move, Q/E down/up, right mouse or Tab to look, Shift fast, mouse wheel scales the speed.
   - **City drive:** **BlackBox > Create City Drive Scene**, then play `Assets/Scenes/CityDrive.unity`: the car
     spawns at the game's free-roam start in L4RA and drives on the city collision while the world streams
     around it (the simulation waits for the ground under the car). Drive demo keys, plus R reset to the
     start, F respawn on the nearest road. The sky follows the camera and the paint reflects the dynamic
     environment map ([city-drive](docs/re/city-drive.md)). Batch PNG:
     `-executeMethod BlackBox.Editor.BatchRender.CityDrive -seconds 3 -out shots`.
   - **Audio browser:** **BlackBox > Audio Browser** lists and plays the game's sounds.

### Command line

```sh
# fast workbench (same Core sources, no Unity)
dotnet run -c Release --project tools/BlackBoxCli -- verify F:/Games/NFSU2
dotnet run -c Release --project tools/BlackBoxCli -- geom F:/Games/NFSU2/CARS/GTO/GEOMETRY.BIN
dotnet run -c Release --project tools/BlackBoxCli -- cars F:/Games/NFSU2/GLOBAL/GLOBALB.BUN

# differential tests against the original code (regenerate goldens first; they are not versioned)
python tools/harness/gen_golden.py            # plus gen_golden_<area>.py per area
dotnet run -c Release --project tools/harness/csharp

# EditMode tests
Unity.exe -batchmode -projectPath Unity -runTests -testPlatform EditMode -testResults Logs/tests.xml

# render a car to PNG (without -nographics)
Unity.exe -batchmode -projectPath Unity -executeMethod BlackBox.Editor.BatchRender.Car -car PEUGOT -out shots/PEUGOT.png
```

## Conventions

- Everything in the repository is in English (code, comments, docs, scripts, UI).
- The simulation lives in game space (X forward, Y left, Z up). Only the Runtime layer converts to Unity.
- `BlackBox.Core` does not reference Unity.
- Every ported behavior cites the address of the original function in `SPEED2.EXE` v1.2.
- No game data or anything derived from it (renders, dumps, goldens) is committed.
