# BYE510 reference review and implementation recommendation

Review date: November 19, 2026. Status: source review completed; no BYE5
binary has yet been built or tested against our CP/M 3 and Z3PLUS images.
The running installation has not been migrated.

## Reference and evidence

The behavioral reference is BYE510, dated August 1, 1986, with its
August 4 local-keyboard correction. CHAT46, dated July 13, 1986, supplies
the reference for two-way chat. This identifies one period configuration;
it does not assert that every RCP/M installation operated identically.

Sources inspected:

- [BYE5 manual](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/bye5.doc.txt)
- [BYE510 source](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/bye510.asm.txt)
- [CP/M Plus installation instructions](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510/b5-cpm3.doc.txt)
- [Local-keyboard correction](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/bye5/bye510.fix)
- [CHAT46 source](https://dflund.se/~pi/cpm/files/ftp.mayn.de/pub/cpm/archive/rcpm/chat46/chat46.asm.txt)

Download sizes and SHA-256 hashes are in `bye510-reference-sources.json`.
Upstream source has been inspected locally, not vendored into this repository.

## Verified operating behavior

The following are source findings, not emulator test results. Key assignments
are configurable assembly defaults. An optional lead-in avoids collisions
when using applications that need the same control characters.

| Operation | Historical behavior and source evidence |
| --- | --- |
| Direct CP/M access | `COMFILE=NO` selects operation without a BBS entry program. |
| Shared keyboard | `MINPUT` accepts local or modem input. `CONIN` applies local function keys through `CKFUNC`. The keyboard correction repairs status polling. |
| Local monitoring | `MOUTPUT` sends normal output to the modem and local console. Console processing is seven-bit; transfer traffic has separate raw modem routines. |
| Private sysop work | `BLNKKEY`, default Ctrl-B, toggles remote blanking. `MSTAT` rejects remote input while muted; `MOUTPUT` then outputs locally only. |
| Privileges | With ZCPR support enabled, `BLNKTOG` enables wheel and sysop drive/user limits during blanking, restoring caller state on return. Shared typing alone does not elevate privileges. |
| Forced disconnect | `TWITKEY`, default Ctrl-N, hangs up and enters logoff handling. |
| Normal logoff | BYE and carrier loss reset the system for subsequent calls. Local `LCKEY`, default Ctrl-L, requests return to local CP/M after the current caller finishes. Automatic return to local operation after every call is not the default model. |
| Operator message | `MSGKEY`, default Ctrl-Q, enters a local message loop. `XITKEY`, default Ctrl-X, ends it. This is not the two-way chat utility. |
| Two-way chat | CHAT46 is a guest program using BYE interfaces. It pages the sysop, accepts a local answer, and supports direct chat. It can suspend and restore the caller time limit. |

The CP/M Plus instructions explicitly build the resident component as an RSX
with RMAC, LINK and GENCOM. `BYE.COM` is a separate entry program and
`B5-DRIV3.COM` carries the RSX. Choosing an RSX here follows the supplied
CP/M 3 implementation; it is not a new architectural preference.

Carrier checking occurs in BYE's I/O paths. This review does not establish
recovery from an arbitrary program that stops making those calls. Likewise,
the source does not establish safe asynchronous interruption of all transfers.

## What our current implementation does differently

`serve_rcpm.py:serve_call` creates a temporary guest, redirects its console
to TCP, and destroys it when the socket closes. `launch_rcpm.zsh --console`
starts another guest. Archive publication supplies independent disk versions.
These mechanisms cannot implement a shared single-machine console merely
by attaching a second terminal.

The earlier `SHARED-CONSOLE-DESIGN.md` also prescribed a host console broker,
exclusive input modes and host chat before this review. Those choices were
premature. BYE already implements shared console I/O and private blanking
inside the guest. Guest chat should be evaluated before adding host chat.

## Recommended first implementation path

First attempt the supplied CP/M 3 BYE5 RSX with a cpmsim machine insert.
Keep the local BIOS console on stdin/stdout and use the emulator's separate
TCP serial channel for modem I/O. tmux can retain the one local console
headless. A host console multiplexer is not required by this approach.

This recommendation is conditional on the compatibility experiment below.
An independently implemented resident replacement remains an alternative
if integration or distribution proves unsuitable. Starting with a host
relay would require rebuilding guest-visible BYE behavior and APIs anyway.

### Concrete emulator gap

Reviewed z80pack revision is the project's pinned
`91fd28eb04e675c2127df88ed3f40675e15282e2`, with our existing patches.
In `cpmsim/srcsim/simio.c`, passive serial channel 1 uses decimal ports
40 (status) and 41 (data). `cons1_in` returns input/output readiness in
bits 0/1. `cons1_out` ignores writes. There is no documented independent
carrier bit or guest hangup/listen control on that pair.

Add an explicit, backward-compatible modem control interface rather than
inferring carrier from data readiness. It must support carrier query,
hangup, answering enabled/disabled, and reliable EOF/reconnect handling.
Do not invent Hayes command parsing for the first dumb-modem configuration.
Normal TCP loss must not stop the emulated CPU: current `cond1_in` and
`cond1_out` include paths that stop it on read/write failure. These paths
need review and targeted disconnect tests, not just a successful echo test.

The machine insert maps BYE's `MDINST`, `MDOUTST`, `MDINP`, `MDOUTP`,
`MDCARCK`, initialization and quit routines onto that interface. Use raw
TCP and preserve all eight data bits. Existing console-based transfers
must be reviewed against the separate raw modem device before migration.

### Compatibility experiment and acceptance gates

1. Build an isolated cpmsim runtime and synthetic test media. Verify serial
   carrier, hangup, EOF, reconnect, busy refusal, and all 256 data values.
2. Obtain the remaining supplied loader sources and clock insert. Configure
   a minimal direct-to-CP/M BYE510 build, including the keyboard correction.
   Use RMAC/LINK/GENCOM as documented and record resulting memory use.
3. Boot disposable copies of our CP/M 3/Z3PLUS media. Check BIOS-vector
   interception, warm boot, RSX coexistence, and actual Z3PLUS wheel and
   environment locations. Do not assume historical low-memory defaults
   describe this Z3PLUS installation.
4. Demonstrate one emulator PID throughout local observation, shared typing,
   blank/unblank, forced disconnect, caller BYE, and a subsequent call.
   Detach and reattach tmux without interrupting the caller.
5. Configure CHAT46 for a system without a BBS and test it separately from
   the operator message key. Recheck raw transfers through the modem path.
6. Only after these pass, integrate archive write policy, WORK cleanup and
   existing persistent uploads/messages, then replace the launcher and guide.
   Keep private archives and the current installation untouched during trials.

The same guest owns P: and J: throughout. Private sysop blanking is the
historical place to enable archive writes; ordinary shared assistance keeps
caller restrictions. Host-enforced write control must be designed around
this transition. Wheel alone cannot isolate arbitrary Z80 programs from
emulator I/O. That is a separate public-deployment concern, not a reason
to replace the shared-console model with independent machines.

### Distribution constraint

The inspected BYE5 notices allow personal copying and unmodified distribution
and restrict fees. The manual also directs installers to configure equates
and supply machine inserts. This is not a general permissive software
license. Permission to distribute our configured or modified version has
not been established. For the experiment, keep upstream code outside git
and keep project-authored insert/build tooling separate. Decide the release
packaging after verifying the applicable terms; do not silently label BYE5
as project-owned open-source code.

## Decision recorded

Prefer a genuine guest BYE5 compatibility experiment over immediately writing
a new host broker.

The operator has approved two compiled configurations in the final package:

| Build | Configuration |
| --- | --- |
| Direct TCP | Serial data and connection controls provided by cpmsim, without Hayes modem commands. |
| tcpser virtual modem | Serial data and modem signals connected to tcpser, with BYE5's existing Hayes support enabled. |

Both builds derive from the same BYE5 core, with configuration-specific
equates and machine inserts. They are alternatives for the same single CP/M
machine. The package must document how to select and install each build,
including the CP/M 3 entry program and RSX driver, and retain reproducible
build instructions. One unchanged binary is not expected to autodetect both
transports. Artifact names will be settled during the build experiment.

This is the packaging target. Bundling configured BYE5 binaries remains
subject to resolving the distribution constraint above and passing the
compatibility checks. Neither configured build has been produced yet.

The next engineering deliverable is the isolated modem-control interface
and its transport tests, followed by the minimal BYE5 build.
