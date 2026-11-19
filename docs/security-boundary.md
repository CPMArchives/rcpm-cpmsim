# Shared-machine security review

Reviewed November 19, 2026. The replacement still runs on disposable media;
the live launcher and private disk set have not been migrated.

## Findings and evidence

| Boundary | Verified implementation | Consequence |
| --- | --- | --- |
| Guest code and resident system | cpmsim `simmem.c` exposes banked RAM; guest-accessible MMU ports select banks and control common-memory write protection. | There is no supervisor/user separation protecting BYE, Z3PLUS or the wheel from a caller's program. A guest-controlled write-protect bit is not a trusted boundary. |
| Native shutdown | `simio.c:hwctl_out` accepts a guest unlock byte and shutdown command on port 160. | A remote caller can execute the native shutdown program regardless of the wheel. The disposable direct-TCP probe confirmed `BYEBYE` followed by `System halted`. |
| Other guest stops | The native shutdown program includes DI/HALT after its hardware-control request. | Blocking port 160 alone does not establish availability. An arbitrary caller program can also stop useful guest execution. |
| Disk writes | `simio.c:fdco_out` writes a guest-selected DMA sector to the selected disk descriptor. | Enforcement must cover raw FDC access, not just BDOS and CCP commands. The original path also indexed the descriptor table without validating the guest drive number; this increment fixes that bounds check. |
| User areas on I: | Raw FDC operations select sectors, not CP/M user areas. | Allowing raw writes to I: does not independently restrict callers to I0:. A BDOS policy can guide normal programs but cannot isolate directory entries against arbitrary raw writes. |
| Host files | Native port 161 calls `host_bdos_out`, which can OPEN/MAKE host files from a guest-supplied FCB. | The RCP/M runtime must not expose this general host-file channel. Dedicated archive/upload interfaces need their own review. |
| Privilege transitions | BYE blanking and the wheel are implemented in writable guest code and data. | Guest notifications of blanking or wheel changes cannot authenticate a local sysop to the emulator. |

The named functions above refer to the pinned z80pack source used by
`build_modem_runtime.py`, not additional source files vendored here.

## Protection implemented by this increment

The runtime builder routes port 161 through a host-side wrapper. Whenever
either RCP/M modem backend is selected, all native host-file requests return
FFh without entering the host-file handler. This applies during local use,
blanking, answering and calls; neither the wheel nor carrier state enables it.
With RCP/M transport disabled, ordinary cpmsim host-file behavior is retained.
The FDC now rejects invalid drive indices before accessing the descriptor
table, in both ordinary and RCP/M modes.

`check_host_boundary.py` boots disposable stock CP/M 3 disks and runs an
actual guest program issuing port 161 OPEN and MAKE requests. It verifies
that both succeed without RCP/M transport, both fail with direct TCP and
IP232 selected, the denied MAKE creates no file, and the existing fixture
retains its original content. No tcpser is needed for this test: the policy
must apply even when no modem or caller is connected.
The same guest probe tries every invalid FDC drive value from 16 through
255 and requires invalid-drive status for each before returning to CP/M.

This closes one channel. It does not establish a complete host sandbox,
archive protection, local-only shutdown, or caller availability isolation.

```sh
python3 build_modem_runtime.py /absolute/path/to/z80pack build/modem/cpmsim
python3 check_host_boundary.py --source /absolute/path/to/z80pack
```

The known shutdown failure is reproducible without touching live disks:

```sh
export PATH="$PWD/build/cpmtools/bin:$PATH"
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser --romwbw /absolute/path/to/RomWBW \
  --autostart --probe-remote-shutdown --output build/bye5/shutdown-probe
```

Currently this intentionally fails on the first direct-TCP call after
BYEBYE stops the guest. Inspect `direct/console.log` for `System halted`.
The ordinary shared-console checks do not send this hostile request.

## Decision needed before privileged takeover

A separate local control channel can authenticate operator intent. It can
also prevent remote input/output before an archive-write gate is enabled.
Those steps alone do not establish that the executing guest is trustworthy:
caller code may have changed a resident routine, a return address or a
buffer earlier. Such code could use newly enabled access after the real
operator requests takeover. Carrier loss must not automatically elevate the
same memory image for this reason.

Two different guarantees must not be conflated:

1. **Period-style access controls.** Retain BYE's shared machine and live
   takeover, apply wheel and directory restrictions to normal applications,
   and require host-authenticated local action for host privilege changes.
   This preserves the agreed experience, but does not promise isolation from
   deliberately hostile guest programs surviving a takeover.
2. **Isolation from hostile guest programs.** Keep archive masters and host
   operations inaccessible to an exposed guest, including after a call.
   Privileged maintenance needs a trusted execution state, obtained through
   a separately designed clean restart or protected execution mechanism.
   A simple local switch or ordinary warm boot is insufficient. This changes
   the live-maintenance experience or requires substantial additional emulator
   architecture, and needs approval before implementation.

The recommended next discussion is to choose the required guarantee
explicitly. Historical authenticity does not itself imply protection from
arbitrary Z80 programs, and public TCP connectivity does not supply that
protection. Until that decision, this increment deliberately adds no privilege
grant keyed to wheel, carrier, a guest OUT instruction, or a local keystroke.
