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

## Historical reference and console ownership

The [BYE510 review](docs/bye510-review.md) records the source findings and
recommended experiment. It supersedes the earlier proposal for a host
console broker, exclusive shared-input modes and host-managed chat.

First evaluate BYE510's supplied CP/M 3 RSX with a cpmsim machine insert.
The local BIOS console remains the operator terminal; the separate TCP
serial device supplies modem I/O. BYE manages their relationship in the
same guest. tmux can retain this console while the local terminal detaches.
The running installation still uses the previous separate-instance design.

| Operation | Intended behavior |
| --- | --- |
| Shared session | Caller and local sysop may type; console output is visible locally and remotely. Local assistance does not elevate privileges. |
| Private sysop work | Explicit remote blanking suppresses modem input/output and enables local sysop privileges. Unblanking restores caller restrictions. |
| Operator message | BYE's local message function writes to the caller and local console. |
| Two-way chat | A configured guest CHAT utility provides paging and conversation. |
| Local offline work | The operator disables answering; one CP/M instance remains in use. |

Control keys must be interpreted only on the local keyboard path. File
transfers use raw modem I/O; the control and chat behavior during transfers
must be verified against the selected transfer software.

## Guest integration and disks

Callers may execute only operator-approved programs and commands, never
arbitrary caller-supplied code. UPLOADS is inaccessible to callers pending
sysop review; WORK holds data and is not an unrestricted program-launch
location. Archive download access does not imply execution permission.
Enforcement must cover alternate launch paths and prevent replacement of
approved programs; see the [security policy](docs/security-boundary.md).
This requirement has been approved but is not yet enforced in the prototype.

Both interfaces use the same mounted P: and J:. There is no publication step
and no reconnect requirement to see completed changes made within this guest.
CP/M remains single-user: monitoring, chat, and takeover do not provide two
independently executing CP/M applications.

Caller BYE ends the call and normally resets BYE to wait for another caller.
A separate operator control requests local CP/M after the call. Caller BYE
must not halt the emulator. Local detach also leaves the guest running.
The native shutdown program is renamed BYEBYE.COM; BYE.COM is remote service.
Explicit operator shutdown must flush guest writes before stopping the machine.

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

Follow the detailed gates in the BYE510 review.

1. Extend the existing serial device with explicit carrier and modem controls,
   preserving existing byte I/O. Verify disconnect, hangup and reconnect.
2. Build the CP/M 3 BYE5 RSX with a project-authored machine insert on disposable
   media. Verify Z3PLUS coexistence, one guest, shared typing and remote blanking.
3. Verify CHAT and transfers, then integrate cleanup and archive write policy.
4. Migrate the launcher and installation guide only after these checks pass.
   Retire snapshots and the separate-console build assumptions from the normal
   installation path. Preserve rollback copies of the existing disk images.

Until the guest lifecycle and privilege transitions are verified, the new
service is a local development path and is not ready for public callers.
