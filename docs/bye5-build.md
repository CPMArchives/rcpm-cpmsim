# BYE5 builds and shared-console checks

Status on November 19, 2026: both configured CP/M 3 BYE510 builds work with
Z3PLUS in isolated tests and now control its actual wheel byte. A missing
valid Z3PLUS environment is refused before answering. This is an integration
milestone, not the final installable disk set. The current live launcher
still uses the earlier architecture.

## Distribution experience and workstreams

The intended release lets an operator put the boot disk, P: archive disk,
J: volume collection and I: work disk in an installation directory, start
the selected connection service, and boot cpmsim. BYE5 belongs on the system
boot disk. Users should not need a compiler, per-caller emulator instances,
or archive-publication commands to run it. Direct TCP uses cpmsim's own
listener; the modem option uses tcpser. A convenience launcher can start
these dependencies and attach the local terminal without changing that model.

The distribution's P: image remains empty. Archive contents, directory
names, welcome/help text and service policies are operator configuration.

The implementation is divided into architecture, security, caller services
and configuration, and sysop management tools. Architecture must expose the
interfaces those later services need. Security is developed alongside it;
configuration of those services can follow once the foundation works.

## What has been built

| Configuration | Files | Behavior |
| --- | --- | --- |
| Direct TCP | `build/bye5/direct/BYE.COM`, `BYEDRIV.COM` | Uses the cpmsim connection device as a dumb auto-answer connection. |
| tcpser | `build/bye5/ip232/BYE.COM`, `BYEDRIV.COM` | Uses the same device through IP232 and BYE5's Hayes initialization/answer logic. |

BYE.COM is the common CP/M 3 entry program. BYEDRIV.COM is a loader with the
configuration-specific BYE5 RSX attached by GENCOM. Each pair is installed
on A: in its test system; install only the chosen pair in a running system.
The original loader's filename reference is configured to A:BYEDRIV.COM.
The stock cpmsim shutdown program is supplied unchanged as BYEBYE.COM in
both build directories. BYE.COM starts or resets remote service and logs a
caller off; BYEBYE.COM terminates the machine. The disk-set installer must
replace the original BYE.COM only after preserving its shutdown function
under BYEBYE.COM. BYEBYE must be restricted to the local sysop. That
restriction has not yet been enforced; renaming the file is not protection.

Project-authored `guest/bye5/cpmsim.ins` supplies the hardware routines.
The configured sources enable CP/M 3, select a nominal 2400-bps maximum,
select Hayes support for tcpser only, and apply Irv Hoff's published
August 4, 1986 keyboard correction. The core remote-console routines remain
upstream BYE5 code. No host console relay implements the shared-console test.

The emulated serial device has no baud clock; baud-selection routines report
success. Tests run cpmsim at 4 MHz to match BYE's configured delay loops.
The direct configuration still follows BYE's period carriage-return speed
recognition procedure. Nominal modem speed is not a TCP bandwidth limit.

The builds enable BYE's ZCPR2-compatible wheel logic, with a project adapter
for Z3PLUS. The old four fixed wheel loads and four fixed wheel stores are
replaced by calls to the adapter. BYE's ordinary state transitions still
choose the values: zero for a new caller, nonzero for private sysop blanking
or local exit, and zero again on unblanking.

`guest/bye5/z3wheel.ins` discovers an environment at initialization rather
than compiling in a wheel address. It searches the supported upper-memory
range 8000h-FEFFh, requiring a JP header, Z3ENV signature, type 80h, and a
matching environment self pointer at offset 1Bh. It obtains the wheel
pointer from offset 29h, as specified by Z3LIB's GETWHL routine. This is
metadata discovery inside the guest, not authentication of the guest.
No match returns to local CP/M without enabling answering. Do not reload
or remove Z3PLUS during a live BYE session; stop BYE first so its next
initialization discovers the current environment.

The runtime ZSHOW observation on the default test system was ENV=F380h and
WHL=F58Bh. Those values are evidence for that configuration, not constants
in the adapter. BYE's legacy speed/max-drive/max-user bytes now live inside
the RSX, avoiding blind writes to historical low-memory locations.
Caller and sysop drive/user maxima are presently P15; per-drive access policy
has not been implemented by this change.

Drive/user policing, clock/time-on accounting, BBS entry programs, welcome
files, and exit hooks remain disabled. Inactivity timeout is configured to
255 as documented for private systems. Shared input, remote blanking,
messages and disconnect controls are provided by the core.

### Security boundary

Verified command-policy behavior is that the Z-System resident ERA command
is denied with the wheel off and works during private sysop blanking.
This does not imply that external ERASE.COM, PIP, arbitrary Z80 programs,
BDOS/BIOS calls, or direct emulator I/O are restricted by that same check.
The adapter does not change host disk permissions or FDC write protection.

A caller program can modify guest memory, including the wheel byte. A
future emulator write-permission gate must not grant authority merely
because the guest wheel byte is nonzero or a guest program requests it.
Local operator authority, pending disk writes at transitions, and leftover
caller code in the shared machine must be considered in the security
workstream before claiming public-operation isolation.

## Reproduce the build

First build the modem runtime and reliable raw cpmtools as documented in
README and `modem-interface.md`. Obtain the pinned z80pack checkout. Then:

```sh
python3 prepare_bye5.py --fetch
python3 build_bye5.py --source /absolute/path/to/z80pack
```

Alternatively, pass `--reference /path/to/reference` to the preparer. That
folder must contain pristine bye510.asm, b5-cpm3.asm and b5-driv3.asm. The
preparer verifies source hashes against `bye510-reference-sources.json`.
With --fetch, missing sources are downloaded to the ignored build cache and
verified before use. Source configuration is written under build/bye5/sources.
Upstream files are never edited or vendored into this repository.

The builder creates its own machine under build/bye5/machine from stock CP/M 3
media and a fresh 4-MB I: image. It removes PROFILE.SUB only from its own boot
copy and runs RMAC 1.1, LINK 1.31 and GENCOM inside CP/M. The full console
transcript is build/bye5/build.log. Commands, configured source hashes,
artifact hashes and the runtime hash are recorded in build-result.json.
The builder has not been pointed at live installation disks.

The direct driver is 4096 bytes; the Hayes driver is 4480 bytes; each entry
program is 512 bytes. These are file sizes, not measured resident-memory
requirements. Distribution of the configured upstream binaries still requires
resolving the notice discussed in the reference review. The binaries remain
local build artifacts for now.

## Repeat the runtime checks

Use the referenced tcpser build and the RomWBW checkout used by the existing
Z3PLUS preparation process. Set PATH to prefer the verified raw tools:

```sh
export PATH="$PWD/build/cpmtools/bin:$PATH"
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser \
  --romwbw /absolute/path/to/RomWBW \
  --output build/bye5/z3checks
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser \
  --romwbw /absolute/path/to/RomWBW --autostart \
  --output build/bye5/autostart-checks
```

The checker creates disposable boot disks, installs the selected pair, and
starts BYE from an interactive CCP prompt. The stock editor is removed from
these test copies to make room for the drivers and test files. Original
media and the operator's installation remain untouched. The checker also exits
remote service locally and verifies that BYEBYE shuts down the emulator.
With `--autostart`, it sends no startup keystrokes and also checks that GET
has announced the return to console input before BYE's sign-on.

The earlier transport-only builds passed the following on stock CP/M 3.
The current builds require Z3PLUS, and the stock-only checker now verifies
that both configurations refuse to answer without a valid environment:

- Two sequential calls use one emulator process.
- A caller executes a transient TYPE command and returns to the CCP.
- Local keyboard input operates that same session and is visible remotely.
- Remote blanking keeps the private test-file output local, and unblanking
  restores remote operation.
- Caller BYE hangs up while cpmsim continues waiting for calls.

Verified again with Z3PLUS loaded, for both configurations, using three calls:

- The same shared-console, transient-command and blanking checks pass.
- The first call ends with BYE, the second with unexpected carrier loss,
  and the third with the local forced-disconnect key.
- A subsequent call works after carrier-loss recovery in the same emulator.
- Every caller fails to erase USERCHK.TXT with the resident ERA command.
  A private sysop can erase SYSCHK.TXT, and USERCHK.TXT still exists afterward.
  These checks verify the wheel-off/on/off transitions against actual file
  operations, including reset to caller restrictions on later calls.

The tests use the default BYE control keys directly. In tmux, Ctrl-B is
also the default prefix; pressing Ctrl-B twice sends one literal Ctrl-B to
the guest for remote blanking. Final key configuration can use BYE's
optional lead-in to avoid application and tmux conflicts.

Logs are retained under each checker output directory. These tests do not
establish protection against arbitrary caller programs, correct WORK cleanup,
file-transfer compatibility, or emulator-enforced archive-write privileges.

## Automatic boot startup

`prepare_z3plus.py --rcpm-startup` configures the existing STARTZ3P alias
command slot to run:

```text
A0:PATH /C A0;A:GET CONSOLE;A:BYE
```

PROFILE.SUB starts Z3PLUS as before. Its startup alias sets the path, ends
CP/M 3 GET console-input redirection, and then starts BYE from Z3PLUS's
remaining command queue. This ordering addresses B5-DRIV3's warning that
loading its RSX within a SUBMIT job lets GET's later removal restore the
console vectors. The alias preparer validates the supplied binary's command
slot and code boundary before editing it; it does not grow the file or
patch executable instructions. BYE.COM and the selected BYEDRIV.COM must
already be installed on A:; this option only configures startup.

Both direct TCP and real tcpser passed automatic startup, three calls in
one emulator, wheel transitions, private output, carrier-loss recovery,
forced disconnect and eventual local BYEBYE shutdown. Existing preparation
without this option retains its PATH-only startup. These checks use
disposable media and do not activate the replacement on the live system.

The supplied Z3PLUS `u10/RELEASE.NOT`, section 9, also describes a distinct
historical BYE compatibility issue: changed SCB bytes can make Z3PLUS think
a SUBMIT job is active and prevent Z-System shells such as ZFILER or LSH
from running. Shell compatibility has not been tested here. Its suggested
binary patch targets a specific older CCP version and has not been applied
to this build. Ending GET redirection is not evidence that this separate
shell issue is resolved.

## Remaining before the disk-set installation is ready

1. Add emulator enforcement of sysop/caller archive-write transitions, using
   trusted local operator authority. The guest wheel integration is now
   working but is not an independent security boundary.
2. Integrate chat, modem-path transfers, persistent upload/message storage,
   WORK cleanup, and recovery policy. Preserve the agreed drive layout.
3. Check Z-System shell compatibility with BYE's SCB changes, as described
   above, before claiming general shell support.
4. Provide the single-machine launcher, selecting direct TCP or tcpser, with
   local tmux detach/reattach and explicit shutdown. Retire the per-caller
   VM and snapshot-publication path from the normal installation.
5. Package the configured boot disk and empty data disks with the complete
   installation guide and the required cpmsim build. Verify security before
   public operation.


## Reference for wheel discovery

The upstream [Z3LIB GETWHL implementation](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/zcpr33/z3libsrc/z3gwhl.z80.txt)
locates the wheel pointer at ENV+29h. The Z3PLUS distribution's DEFAULT.Z3P
records MAXDRV as 1-16 and MAXUSR as 0-15; those are not interchangeable
with every historical BYE limit byte. The adapter therefore changes the
wheel linkage without pretending to enforce a new directory policy.
