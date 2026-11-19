# Architecture completion gates

The operator has approved completing architecture first, including mechanisms
used by security, and configuring security policy afterward. This distinction
does not mark the replacement installation as ready for public callers.

## Architecture scope

| Gate | Current evidence | Remaining work |
| --- | --- | --- |
| One persistent machine | Direct TCP and real tcpser pass successive calls in one CP/M 3/Z3PLUS guest. | Integrate the replacement installation and launcher. |
| Shared console | Local monitoring, shared typing and private blank/unblank pass. | Integrate CHAT and verify control behavior during transfers. |
| Boot | Z3PLUS and the chosen BYE RSX start automatically after GET redirection ends. | Include this startup in the installation builder. |
| Call boundaries | BYE, carrier loss and forced disconnect pass shared-console checks. Tests also seed pending commands before blank/unblank and call termination, including a transient waiting for console input. | Verify shell/ZEX/SUBMIT state and define bounded recovery for applications that stop polling BYE. |
| Operator state | BYE changes the actual Z3PLUS wheel; private output stays local. | Complete local/remote transition and shutdown mechanisms, including guest buffer handling and host disk-write control. |
| Disk ownership | The shared-machine design uses the same I:, J: and P: for caller and sysop. | Exercise live J: mounting and completed archive changes in the integrated machine; remove publication from the normal workflow. |
| Persistent services | Upload and message persistence work in the earlier prototype. | Move the transfer/service path onto the separate modem device; preserve completed submissions through call recovery. |
| Disposable work | I0: WORK is designated for per-call data. | Clear WORK through a guest-safe lifecycle path, preserving uploads/messages and CP/M filesystem consistency. |
| Transfer interfaces | Earlier prototype supports several protocols; the new modem device passes binary transport tests. | Verify the promised X/Y/ZMODEM and Kermit paths with the shared BYE machine. Binary echo alone is insufficient. |
| Installation | Both BYE variants and the required cpmsim runtime build reproducibly. | Supply a single-machine launcher, detached console, empty distributable data disks, documented startup/shutdown and rollback-safe migration. |

## Deferred security configuration

Choose and configure the approved caller programs, wheel-protected commands,
directory visibility/passwords, upload review rules, application options and
operator-specific access policy after the underlying mechanisms work. The
prohibition on arbitrary caller code remains a requirement; defer its concrete
command/directory configuration, not the ability to enforce it.

The architecture must provide safe privilege and lifecycle transitions and
protect the host interfaces. It need not settle the final program list,
directory passwords, welcome text, message-board choice or archive contents.
Additional software services must not silently bypass those mechanisms.

The live installation remains on the earlier separate-instance architecture.
Complete and verify the replacement on disposable media before migrating it.
