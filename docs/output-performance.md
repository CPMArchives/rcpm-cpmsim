# Console output investigation — 20 November 2026

The 4 MHz cap exposes a real cost in the current CP/M 3/BYE output path.
It does not mean that 4 MHz CP/M intrinsically has a 2400-baud output limit.
Raising the clock speeds this code up, but is not the preferred first remedy:
it also changes games, software delays, autobaud windows and timeout loops.
The initial investigation left production unchanged. The subsequent BYE fix
below removes the avoidable waits; the CPU default and permission policy remain
unchanged.

## Findings

1. **BYE's original keyboard-status timer spins for about one emulated
   millisecond when no input is available.** CP/M polls keyboard status during
   ordinary console output. Thus the inactivity-clock mechanism delays output
   even though neither the network nor terminal requests pacing.
2. **Our BDOS permission dispatcher also scans file-function tables for console
   calls.** The dispatcher body costs 1,426 T-states per call in the measured
   build (excluding its short wheel getter). It has nothing to reject for those
   console functions, but still takes the general route.
3. The actual network backend has no baud-clock sleep. The same slow output was
   reproduced using a raw socket client, so SyncTERM/tcpser is not required to
   produce it. SyncTERM's "Current" rate semantics were not established and
   are not part of this diagnosis.

## Controlled measurements

A disposable TYPE.COM probe emitted 512 ASCII X characters, bracketed by profiler
markers. An isolated emulator counted instruction T-states by memory bank and
program counter. Startup, command parsing, file loading and shutdown were outside
those windows. The configured CPU target stayed at 4 MHz. Wall times also include
normal host I/O and scheduling; instruction counts provide the stronger cost
comparison. The original release and operator installation were not modified.

| Output route | BYE/caller state | T-states per character | Approx. characters/s |
| --- | --- | ---: | ---: |
| BDOS 2, character output | BYE removed | 1,925 | 1,820 |
| BDOS 2 | BYE active, caller blanked | 2,629 | 1,285 |
| BDOS 2 | BYE active, caller public | 8,895 | 387 |
| BDOS 6, direct character output | BYE active, caller public | 2,729 | 1,265 |
| BDOS 9, string output | BYE active, caller public | 7,034 | 487 |

"BYE removed" is the same CP/M 3/Z3PLUS guest after BYE's normal local exit,
not a different operating system. The direct-BIOS-function-50 samples in the
full data include CP/M's BIOS-call parameter copying; they are not a zero-overhead
bare BIOS baseline.

For public BDOS 2 output, the keyboard delay accounts for approximately **46%**
of all emulated instruction cycles. The permission dispatcher body accounts for
another **16%**. For public BDOS 6, which avoids that keyboard delay, the same
dispatcher is **52%** of the smaller total. BDOS 9 pays the dispatcher once for
the whole string, but still hits the keyboard delay for each character.

The earlier end-to-end TYPE WELCOME.TXT measurement was about 218 bytes/s at
4 MHz and 1,094 bytes/s at 20 MHz. That includes the actual file-reader path,
line breaks and BYE's null padding. Do not equate those byte rates directly
with the synthetic X-character rates above or claim that every utility uses
exactly the same output sequence.

## Evidence for the delay

Upstream BYE510's MSTAT3 calls KDELAY before decrementing its polling-based
inactivity counter. KDELAY loads `42*MHZ` into BC and spins through DELAY1.
With MHZ=4, this is 168 loop iterations. The profiler observed exactly
512 × 168 = 86,016 iterations for a 512-character BDOS 2 sample. It saw the
same count for BDOS 9 and none for BDOS 6 or blanked/private operation.

A second **test-only** runtime temporarily replaced just the MSTAT3 delay call
with NOPs inside the marked benchmark window, restoring it immediately afterward.
Carrier checks and the file-access dispatcher were left in place. This isolates
cost; it is not a releasable timer fix.

| Public output route, still 4 MHz | Before | Without the artificial wait |
| --- | ---: | ---: |
| BDOS 2 | 387 characters/s | 721 characters/s |
| BDOS 9 | 487 characters/s | 1,186 characters/s |
| BDOS 6 | 1,265 characters/s | 1,264 characters/s |

The unchanged BDOS 6 result is a useful control. Its code did not enter that
wait in either runtime. Simply deleting the wait in production would make the
existing polling-based inactivity clock run too quickly and is not recommended.

## Changes and remaining options

1. **Implemented: early route for BDOS functions 0-12.** Forward those calls
   to the existing BYE handler before walking the file-permission tables.
   Preserve every check for file access, program loads, private DUs, A: writes,
   board-entry exceptions and call-boundary cleanup. Review the exact function
   list and run the existing security checks on both driver builds.
2. **Implemented: separate inactivity timing from status polling.** Make status checks
   nonblocking while retaining a real elapsed-time timeout. A read-only
   monotonic stopwatch uses port 74; paired reads latch elapsed whole minutes
   and an output resets it. This leaves the OS's interrupt timer unchanged.
   Do not commandeer that interrupt timer,
   call non-reentrant BDOS clock functions from inside console handling, or
   remove deliberate modem-initialization delays indiscriminately.
3. **Deferred: explicit operator CPU-speed setting. The default remains 4 MHz.**
   A faster CPU is useful for throughput experiments, but changes instruction-
   timed programs and BYE's remaining delay loops. Qualify timeout/autobaud
   behavior before recommending higher or unlimited clocks.
4. **Keep connection pacing separate.** Client display pacing or optional
   virtual-modem throttling can provide a slow-connection experience without
   speeding up game logic. Currently the distributed GAMES libraries are for
   download, not caller execution; eventual online games need their own review
   and a deliberate clock policy.

These are incremental improvements; no CPU clock needs to be increased merely
because a status poll contains an avoidable wait. First remove that coupling,
then measure the remaining overhead and choose defaults on evidence.

## Corrected build measurements

Using the installed `TYPE A:WELCOME.TXT [NO PAGE]` in a disposable native
package at 4 MHz, three runs returned 684 bytes in 1.1573, 1.1434 and 1.1442
seconds: 591-598 bytes/s, versus approximately 218 before (about 2.7 times
faster). These end-to-end samples include command processing and file reading.
They do not establish instantaneous output. A complete `DIR P: /N` of the
310-library SIGM area took 37.8787 seconds for 6556 bytes, including directory
search and processing; that total is not a measurement of TCP bandwidth.

The initial one-minute timeout samples occurred after 60.094 seconds with no
renewed activity and 59.846 seconds after renewed activity. Both were at 4 MHz:
the initial test incorrectly labeled the first sample 20 MHz because it wrote
only CPU-speed port 30. This device requires writing the high byte to port 31
to commit a clock change. The corrected test writes both ports and reads back
the selected speed before timing. The test-only probe is excluded from release
media. The activity-reset test sends input at 30 seconds, restarting the minute.

The corrected, read-back-verified runs expired after 59.952 seconds at 20 MHz
and 59.854 seconds after renewed activity at 4 MHz. Both recovered to answering.

## Comparing the earlier launch path

The legacy `launch_rcpm_cpm3.py` and `serve_rcpm.py` launch cpmsim without `-f`.
The preserved cpmsim source defines `CPU_SPEED` as zero (unlimited). In contrast,
`run_shared_trial.py` has explicitly selected `-f 4` since its initial November 19
commit, and the native package also selects `-f 4`. An earlier user-provided
shutdown screenshot reports 19.41 MHz. These establish different available
launch paths and an observed faster session; they do not establish which exact
session the user recalls as instantaneous.

In one disposable corrected-build instance, the same 684-byte TYPE response
took 1.1434 seconds at 4 MHz (598 bytes/s) and 0.3253 seconds at a read-back-
verified 20 MHz (2102 bytes/s). Only the CPU clock changed between samples.
This supports CPU throttling as an explanation for a visible output difference,
without proving the historical session's configuration. No production setting
was changed for this comparison.

Retain 4 MHz as the package default: the current scrolling is acceptable to the
operator, and the faster session did not qualify timing-sensitive software.
Higher-clock console throughput is not evidence of game compatibility.

## Artifacts

- `docs/performance/console-output-2026-11-20.json`: exported counts, wall times,
  top instruction addresses, dispatcher totals and the controlled comparison.
- `build/output-profile/`: experimental source, probe assembly, instruction
  counters, snapshots and private test-instance logs. These are lab artifacts,
  not code installed by the release launcher.
- Relevant source labels: upstream BYE510 `MSTAT`, `MSTAT3`, `KDELAY`, `DELAY1`;
  project `guest/bye5/privateb.ins` (`WXBCHK`, `WXBFNL`, `WXBOK`) and
  `guest/bye5/cpmsim.ins` (`MDOUTST`, `MDOUTP`, `MDCARCK`).
