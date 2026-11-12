# The Crew Motorfest on Linux: a Radeon-only Vulkan workaround

[Investigation and evidence](docs/investigation.md)

**One affected system, two days of investigation, one effective launch option.**

On an AMD Radeon 8060S Linux system, The Crew Motorfest failed at startup with a Wine Vulkan assertion. Restricting Vulkan driver discovery to Radeon made the game display graphics and run smoothly, according to the tester. This repository documents that result—not a universal fix or a proven upstream root cause.

## Try the workaround

**For Linux systems using the Mesa RADV driver for an AMD GPU.** In Steam → game Properties → General → Launch Options:

```sh
VK_LOADER_DRIVERS_SELECT=radeon_icd* %command%
```

The Vulkan loader filters discovered driver **manifest filenames**. This keeps names such as `radeon_icd.x86_64.json` and `radeon_icd.i686.json`, excluding software drivers such as Lavapipe/llvmpipe. It affects this game's process tree, including its launcher, not all applications on the system.

- Do not blindly use this pattern for NVIDIA, Intel, AMDVLK, or AMD proprietary drivers: if no manifest matches, Vulkan will not have a usable driver.
- Requires loader support for driver filtering (introduced with Vulkan headers 1.3.234). The observed system loaded Vulkan loader 1.4.341.
- It filters drivers, **not individual GPUs**. Multiple GPUs exposed by RADV may remain visible.
- To undo, remove this option. On the affected system that may restore the original failure.
- If you already have launch options, preserve them before editing; do not accidentally remove required options.

No reinstall, prefix reset, game-file patch, system-wide driver removal, or anti-cheat modification is involved.

## Matching symptom

A Wine C++ Runtime assertion dialog named the game and reported:

```text
File: ../src-wine/dlls/winevulkan/loader_thunks.c
Line: 6860
Expression: !status && "vkResetCommandPool"
```

The line number is build-specific. The assertion alone does **not** establish that the device was NULL; a new Vulkan trace established that separately.

## What changed in the trace?

| Failing logged launch | Successful logged launch |
| --- | --- |
| Both Radeon 8060S and llvmpipe enumerated | Only Radeon enumerated |
| Device creation logged for both | Only Radeon device creation logged |
| `vkResetCommandPool (nil), 0x0, 0` observed | No NULL reset in the inspected success log |
| Assertion dialog | Tester reported rendered graphics and smooth operation |

The successful run used the same Wine Vulkan logging settings as the failure baseline. The intentional functional change was the driver filter. **An A→B success was observed; a B→A reversal, repeated cold launches, extended gameplay, and an independent launch with the minimal no-logging option were not verified in this investigation.** The exact bug could still be in device selection, a separate initialization/cleanup path, Wine, or another component.

## Tested environment

- Fedora 44
- AMD Radeon 8060S Graphics, RADV STRIX_HALO
- Software Vulkan device: llvmpipe, LLVM 22.1.8
- Vulkan loader 1.4.341
- Steam App ID `2698940`
- Custom compatibility tool `PROTON_LG_10-30`

These identify the observed setup; they are not installation recommendations or proof that other versions are affected. The exact Mesa package version was not captured in the final fresh baseline.

## Optional tools

The launch option above is sufficient; scripts are optional.

- [`scripts/run-radeon.sh`](scripts/run-radeon.sh): portable wrapper for non-Steam/manual commands. No logging, debugger, or disk changes.
- [`scripts/summarize-vulkan.py`](scripts/summarize-vulkan.py): reads an existing Wine Vulkan trace and prints only selected event counters and sanitized evidence. Can restrict by **Wine PID**, avoiding launcher/game log confusion. It does not launch or attach to anything.

```sh
bash scripts/run-radeon.sh /path/to/your/launcher argument
python3 scripts/summarize-vulkan.py /path/to/steam-2698940.log --pid 0504
python3 -m unittest discover -s tests -v
```

For a short diagnostic run, Proton can produce a trace using:

```sh
PROTON_LOG=1 WINEDEBUG=-all,+timestamp,+pid,+tid,+vulkan %command%
```

This is **not** a daily launch option. Vulkan traces grow quickly during gameplay; stop the diagnostic run promptly, then remove logging options. Proton may replace the previous `~/steam-2698940.log` on a later launch, so preserve needed evidence first. Raw logs can contain personal paths and other private data: do not publish them unreviewed. See [privacy and troubleshooting](docs/investigation.md#privacy-and-repository-scope).

## Slow before the game even starts?

This investigation also encountered a separate Steam delay at `CheckShaderDepotManifest`, before Wine/game processes existed. Moving only this game's shader cache aside and disabling shader pre-caching/background processing restored normal launch speed in the reported setup. Those changes were not isolated from each other, and are not required by the Radeon workaround. See the [separate startup-delay note](docs/investigation.md#separate-problem-steam-launch-delay) before clearing anything.

## Reporting another result

Include GPU/driver/loader/Proton versions, whether software Vulkan devices are present, the exact symptom, the filter used, and whether it changes actual enumeration. State whether you reached a playable scene, not just whether the dialog disappeared. Review any excerpts before sharing. Reports of failures are useful too.

## References

- [Khronos Vulkan Loader: driver filtering](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md#driver-filtering)
- [Wine Vulkan source](https://gitlab.winehq.org/wine/wine/-/tree/master/dlls/winevulkan)
- [Valve Proton: runtime configuration](https://github.com/ValveSoftware/Proton#runtime-config-options)

MIT-licensed helper code and documentation. No game binaries, downloaded compatibility tools, account data, or original raw logs are distributed.
