> Current release work is tracked in [the 1.0 release plan](release-1.0-plan.md).
> The gate inventory below preserves earlier investigations; it is not the
> remaining-release checklist. Current caller policy is documented in
> [caller execution](caller-execution.md), including AUTH and actual F4 checks.

# Architecture completion gates

## Current launcher and recovery status — 20 November 2026

The default launcher now selects the existing single shared upper-area system,
with tmux start/reattach and instance/port ownership checks. The separate-instance
launcher is retained as `launch_legacy_rcpm.zsh`. New upper-area builds generate
shared start and cold-backup helpers. See [operations](shared-operations.md).

Cold backup, checksummed restore, existing-target refusal, live-disk lock refusal
and a restored populated guest accepting a caller pass in
`build/shared-operations-check-final/result.json`. tmux session reuse and ownership
guards pass with an adapter; actual tmux server attachment is unverified because
the development sandbox denies server access. The operator’s live installation
has not been stopped or backed up by these checks.

## Earlier architecture gate inventory

The table below records earlier investigation gates; its B: layout and
separate-instance deployment statements are historical, not current operation.

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
| Private system tools | The new builder separates SYSUTILS B: from public A: services and stores BUILD outside the mount collection. Both BYE variants gate caller BDOS file access to B:. | Configure remaining directory permissions and operator workflows. |
| Caller execution | Both BYE variants permit loads only from the compiled A0: approved-program list, deny caller A: writes, and preserve native resident-command wheel checks. The builder makes RCP WHL require existing privileges. Both backends pass source spoofing, boot-tool denial, local transitions, call boundaries and executable-file download checks. | Review each future approved application and its options; retain the validated CPR/RCP configuration. |
| Persistent services | X/YMODEM uploads and saved MESSAGE files persist across shared-machine calls on both backends. Partial uploads and unsaved drafts are discarded. | Integrate these verified interfaces into the installation; configure review/release policy later. |
| BBS application | The RBBS 3.7 evaluation now admits callers through a fixed A0:RBBS launcher, with one-attempt permission for the trusted A15:RBBS37 load. I15: data (legacy I2:) stays private outside the trusted board context. Both transports pass caller entry from WORK:, registration, message post/read, J/G and carrier-loss recovery without wheel elevation. | Qualify database-write recovery and board policy before public service. |
| Disposable work | Native BDOS cleanup removes I0 files, including read-only/system files, before answering. Tests preserve I1 and the host inbox; a read-only WORK disk disables answering. | Include the required writable I: in installation and migration checks. |
| Transfer interfaces | X/YMODEM uploads and binary J: YMODEM downloads pass with BYE over direct TCP and real tcpser. | Integrate XMODEM downloads, ZMODEM, Kermit and transfer-time operator controls. |
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

The earlier live installation used the separate-instance architecture.
Complete and verify the replacement on disposable media before migrating it.
The [shared-service build and check procedure](shared-services.md) records
the transport and WORK-cleanup integration completed so far.
