# Shared local and remote RCP/M console

## Agreed operating model

The installation represents one persistent CP/M 3 computer. A remote caller
and the local sysop observe the same guest session. Local attachment does
not boot another guest. The guest continues running when the local terminal
detaches. Only one remote caller controls the guest at a time.

This supersedes the separate local and disposable caller machines and their
archive publication workflow. The current code still implements that older
architecture. This document records the replacement requirements, not a
completed migration.

## Console ownership

A background service owns the emulator PTY, the network listener, and a
local-only operator endpoint. A local terminal client attaches through that
endpoint. tmux hosts the terminal client if desired; it does not determine
the guest lifetime. Operator access must be restricted to the host owner.

The service duplicates guest output to the local observer and the connected
caller. File-transfer bytes must reach the caller unchanged. Local display
of binary transfer traffic can be suppressed without consuming or modifying
the caller's stream. Slow or detached observers must not stall transfers.

Explicit modes govern input and output:

| Mode | Guest input | Caller receives |
| --- | --- | --- |
| Local operation | Sysop keyboard | No caller admitted to privileged session |
| Caller operation | Caller keyboard | Guest console output |
| Chat | Guest input paused; both keyboards go to chat | Chat text |
| Sysop takeover | Sysop keyboard; caller input suspended | Status or an explicit supervised view |

Chat must suspend guest input while retaining and safely handling guest
output. Entering chat or takeover during a transfer requires a defined
transfer-completion or cancellation path; arbitrary byte injection is unsafe.
Returning control requires restoring caller privilege and disk policy first.

## Guest integration and disks

Both interfaces use the same mounted P: and J:. There is no publication step
and no reconnect requirement to see completed changes made within this guest.
CP/M remains single-user: monitoring, chat, and takeover do not provide two
independently executing CP/M applications.

Caller BYE ends the call and returns control to the operator service. It must
not halt the emulator. Local detach also leaves the guest running. Explicit
operator shutdown flushes guest writes before stopping the machine.

Carrier loss must revoke caller input, recover guest execution, clear only
the disposable WORK area, and preserve completed uploads and messages.
The existing disconnect-and-destroy mechanism cannot supply this behavior.
Recovery must address hung applications, not assume the CCP is accepting input.

Sysop and caller privileges must transition within this one guest. Wheel state
alone does not protect against arbitrary Z80 programs issuing BIOS or emulator
I/O directly. Host-enforced archive write protection must follow operator
mode, and the remote connection must never activate that mode. Local takeover
must revoke caller access before write privileges are enabled.

## Incremental implementation and acceptance

1. Add the persistent service and owner-only local client. Verify a single
   emulator PID, shared output, byte-exact transfers, local detach/reattach,
   and rejection of a second remote caller. Keep the old installation intact.
2. Add exclusive input ownership, chat and takeover, including transfer
   handling and local controls that cannot be invoked by remote bytes.
3. Integrate guest logoff, carrier-loss recovery, WORK cleanup, and privilege
   transitions. Verify uploads/messages survive and archive protections return
   before another caller receives control.
4. Migrate the launcher and installation guide only after these checks pass.
   Retire snapshots and the separate-console build assumptions from the normal
   installation path. Preserve rollback copies of the existing disk images.

Until the guest lifecycle and privilege transitions are verified, the new
service is a local development path and is not ready for public callers.
