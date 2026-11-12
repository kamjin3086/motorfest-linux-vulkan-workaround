# Investigation: observations, limits, and useful lessons

Recorded 2026-11-12. This is a curated case study, not the original working notebook. Early conclusions were revised when fresh evidence contradicted them.

## Fresh failure baseline

The game used custom Proton `PROTON_LG_10-30`. A historical Steam launch override disabled `amd_fidelityfx_vk`. Removing it was verified in the process environment; the game's FidelityFX DLL then appeared in its mappings. The assertion persisted. This did not establish that every FidelityFX-related path was irrelevant.

A new run used Wine's `+vulkan` trace with no debugger. The trace was separated by Wine PID so that 32-bit launcher activity was not mistaken for game behavior.

Selected facts from that game process:

1. Enumerated Radeon 8060S and llvmpipe.
2. Logged successful device creation for llvmpipe.
3. Logged successful device creation for Radeon.
4. Later reset a command pool with a non-NULL device.
5. Immediately afterward, on the same thread, called reset with a NULL device and zero pool.
6. The tester observed the assertion dialog.

A non-NULL device alone is not enough to identify the owner of an internal game object. This trace does not prove which subsystem issued the bad call, nor that all other initialization was successful.

In Wine's thunk pattern, `status` in the assertion is the bridge call's status, not simply the Vulkan function's `VkResult`. Do not interpret the dialog as a driver returning a particular Vulkan error code.

## Intervention and observed result

The next run retained the same targeted Wine logging, changing the log destination to isolate evidence, and added:

```text
VK_LOADER_DRIVERS_SELECT=radeon_icd*
```

The variable's actual presence was checked in the game environment. The success trace enumerated one device, Radeon 8060S; inspected creation records named only Radeon. No NULL reset was found at inspection time. No debugger was attached. The tester reported visible graphics and smooth operation.

The [short excerpts](../evidence/observations.txt) preserve only relevant lines, omitting addresses and time/process identifiers where unnecessary. They are curated observations, not a complete replayable trace.

### What is supported

Excluding non-Radeon Vulkan ICD manifests was an effective workaround on the observed machine. Software-device participation / multiple-driver visibility is a useful discriminator for this symptom.

### What is not established

- That llvmpipe itself is defective or the game was primarily rendering on the CPU.
- Which exact subsystem used the NULL handle.
- Whether a game bug, Wine behavior, driver behavior, or their interaction is ultimately responsible.
- Whether another non-Radeon driver, rather than llvmpipe alone, is relevant: the filter removes all nonmatching manifests.
- Generality across Mesa/Proton/game versions or other GPUs.
- B→A reversal, repeated cold starts, long-term gameplay, or an independently confirmed no-logging launch.

A good follow-up is to validate the minimal launch option with no diagnostic logging. A reversal test is optional if the user wants stronger causal evidence; do not demand more failure reproduction from someone who just wants to play.

## Why debugger scripts were removed

One attempt installed software entry/return breakpoints. The game produced a `SIGTRAP`, causing the first implementation to detach prematurely. A revised signal-forwarding loop then repeatedly handled a trap at the same PC, consuming almost a CPU core and severely delaying startup. Stopping the observer interrupted GDB, and detach was verified.

A native `ms_abi` test program had passed, but did not exercise Wine's exception dispatch. That test was insufficient. A later hardware-only probe was never attached in its attempted run because Steam was still waiting before game process creation.

Some old scripts also used incorrect Vulkan structure offsets. Those field values were not retained as evidence. No script that mutates arguments, bypasses an assertion, changes anti-cheat, kills all Wine processes, or cleans a prefix is needed for the published workaround.

**Lesson:** instrumentation is an intervention. First establish a non-debugger baseline, bound probe time/output, and do not turn a probe failure into a game diagnosis.

## Separate problem: Steam launch delay

Before Wine started, Steam sometimes waited at `CheckShaderDepotManifest`. Local console logs showed waits of 186 and 77 seconds on earlier launches; another launch remained at that task when checked. At that moment no game, Ubisoft launcher, wineserver, or GDB process existed. This is distinct from the debugger-induced delay above and from the game's later assertion.

After normally exiting Steam, only this game's approximately 539 MiB shader-cache directory was moved aside. Shader pre-caching/background processing was also discussed with the tester. The tester then confirmed normal launch speed. The exact UI toggle state was not independently inspected, and the two interventions were not individually tested.

This does **not** prove that a damaged cache or any specific network condition caused the delay. It does not justify deleting all Steam caches or modifying DNS/firewalls.

### If you choose to try that separately

1. Exit Steam normally and ensure no affected game/cache compiler is running.
2. Find the affected library's `steamapps/shadercache/2698940` directory. Installation paths vary.
3. **Move it aside as a backup**, outside `shadercache`; do not delete it permanently.
4. If the Steam version exposes shader pre-caching/background-processing settings, record their original states before changing them.
5. Test startup. Disabling pre-caching may cause more runtime shader compilation stutter.
6. To restore, exit Steam, move any newly generated cache aside, and move the original directory back. Restore recorded settings. Do not merge caches blindly.

Do not remove `compatdata/2698940`, user saves, game files, or account data as part of this cache operation. Clearing Steam's download cache is a different action and was not part of this fix.

## Privacy and repository scope

The original working directory included raw logs, process environments, local account paths, downloaded tools, prefix material, experimental scripts, and binary test artifacts. It was moved to a private archive outside this repository. No original Git history existed to sanitize; this repository starts from the curated files.

The helper summarizer prints only selected event types, fixed GPU classes, and event counts. It does not forward arbitrary log lines or paths. Its output is deliberately incomplete and should still be reviewed before publication. Public excerpts are included explicitly; raw logs are ignored by Git and must not be force-added without review.

The wrapper simply sets one environment variable for the supplied command. No service restart, system networking change, or persistent driver change is made.

## Primary references

- [Vulkan Loader driver interface and filtering](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md)
- [Vulkan Loader filter syntax](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderInterfaceArchitecture.md#filter-environment-variable-behaviors)
- [Wine Vulkan source](https://gitlab.winehq.org/wine/wine/-/tree/master/dlls/winevulkan)
- [Proton runtime options](https://github.com/ValveSoftware/Proton#runtime-config-options)
- [GDB signal handling](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Signals.html)
