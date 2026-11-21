# Shared-machine security review

Current policy: [unified drive/DU authorization](caller-execution.md). AUTH
replaces the older drive-specific file gates and compiled A0 filename grants
described in the historical review below. Caller read/write access defaults to
deny; private sysop mode bypasses those permissions. Execution requires R,
no W, and actual F4. A:, J: and P: share the same write-protection mechanism.

Reviewed November 19, 2026. The replacement still runs on disposable media;
the live launcher and private disk set have not been migrated.

Current additions are documented in [caller execution](caller-execution.md)
and the [RBBS boundary](rbbs-trial.md#public-launcher-permission): the fresh
upper-area profile uses I13:SYSUTLS, read-only I14:HELP and private I15:RBBS.
A0:RBBS grants one specific trusted board load without wheel privileges.
The older B: layout and initial negative findings below remain historical
evidence, not a description of the complete current guest policy.

The newer [SYSUTILS disk layout](system-disk-layout.md) moves BYEBYE and
maintenance programs to B:, with a BYE BDOS gate denying caller B: access.
`check_sysutils.py` verifies that boundary on both modem backends. The
shutdown probe below deliberately retains BYEBYE on public A: to demonstrate
the older unrestricted layout's failure; it does not build the SYSUTILS layout.
The [approved caller execution mechanism](caller-execution.md) now restricts
loads to the compiled A0: program list, protects A: from caller writes, and
makes the RCP WHL command require existing operator privileges. Boot tools
are excluded from the caller list. Full directory/application security
configuration remains work to do.

## Approved caller execution policy

See the [period configuration evidence](historical-rcpm-security.md) for
operator accounts supporting a selected-utility configuration, and for
historical command-buffer cleanup requirements.

The operator has specified: "Callers should never have the ability to run
arbitrary code on the rcpm."

Callers may run only operator-approved programs and commands. Uploaded files
are confined to UPLOADS and are unavailable for caller execution, copying
or retrieval until reviewed and explicitly released by the sysop. WORK is
for caller data; writing a file there must not make it executable. Archive
downloads do not imply permission to execute archive contents on the system.

This preserves the single shared CP/M machine and live local takeover.
It does not authorize a new guest per call or a restart before every takeover.
The earlier choice between period-style controls and isolating arbitrary
hostile guest programs did not account for this execution policy.

Enforcement remains to be implemented and verified. In particular:

- Restrict execution to approved program contents in locations callers cannot
  modify. An approved filename or extension alone is insufficient.
- Cover explicit drive/user filenames, named directories, command search,
  aliases, scripts and application launchers. PATH configuration alone is
  not an execution boundary.
- Prevent callers from replacing an approved program or making a modified
  copy eligible for execution under the same name.
- Review debuggers, memory editors, program loaders, interpreters and
  applications that execute other programs or caller-supplied machine code.
  Approval of the outer program must not silently approve arbitrary code
  supplied to it.
- Keep BYEBYE and other sysop-only tools unavailable to caller execution.
  Keep host-side protections independent of guest command policy.

The approved program set and application compatibility need review before
choosing the enforcement mechanism. This policy reduces the intended attack
surface; it is not evidence that the current build enforces it or that an
approved program cannot contain a vulnerability.

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

With the current execution adapter this should pass: BYEBYE on A: is not an
approved caller load, and the guest remains available. Before that adapter
was introduced, this probe demonstrated `System halted` on the first call.
The ordinary shared-console checks do not send this hostile request.

## Residual risk at privileged takeover

A separate local control channel can authenticate operator intent. It can
also prevent remote input/output before an archive-write gate is enabled.
Those steps alone do not establish that the executing guest is trustworthy:
if execution policy is bypassed, caller code may change a resident routine, a return address or a
buffer earlier. Such code could use newly enabled access after the real
operator requests takeover. Carrier loss must not automatically elevate the
same memory image for this reason.

The next design task is enforcement of the approved caller execution policy
alongside local authority and disk protection. Do not treat a caller's ability
to launch arbitrary programs as an intended feature. Equally, do not claim
that wheel settings or upload placement alone enforce the policy. No privilege
grant keyed to wheel, carrier, a guest OUT instruction, or a local keystroke
has been implemented by this review.
