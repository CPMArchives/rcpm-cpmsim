# Native Debian service kit

Engineering candidate. Installer, systemd lifecycle, reboot and recovery checks
have been exercised in a disposable Debian 12 ARM64 VM. The accompanying
VM-VALIDATION.json records exact artifacts, coverage and limits. No x64 VM,
public VPS deployment or 72-hour VPS soak is claimed. CPMNet is not implemented here.

## Build an offline installation kit

Build on the matching Linux architecture using Python 3.9+, cc, make and
binutils. Start from the published native Linux package, not a live board.
Download the go4retro/tcpser source archive for commit
fe7feff4862406b277e009d14c219f5d16cf1222 from:
https://api.github.com/repos/go4retro/tcpser/tarball/fe7feff4862406b277e009d14c219f5d16cf1222
The builder requires SHA256
b70e9b222e7dbdcc2fb0395caf444f1ddd329f5d9958b5895a5e921fed2bbc68.
It bundles the compiled modem, complete corresponding source and a build receipt.

    python3 build_native_service_kit.py --package rcpm-v1.2.1-linux-arm64.tar.gz \
      --tcpser-source tcpser-source.tar.gz --output build/native-service

No installation, network download, public listener or service start occurs
while building. Base package common files remain unchanged. The resulting kit
has additional standard-library Python service helpers; ordinary interactive
Start-RCPM.sh still requires no Python. Do not publish this engineering kit as
a qualified release before completing target-host checks.

## Install (operator action, not part of tests)

Extract the kit on matching Debian. Python 3.9+ and systemd must already exist;
no compiler, pip packages or network downloads are required during installation.

    ./Install-Service.sh --check
    sudo ./Install-Service.sh --install

The installer refuses existing data/configuration/service units. It creates an
unprivileged rcpm account, copies the installation into /var/lib/rcpm/instance,
installs root-owned helpers under /usr/local/lib/rcpm, units and /usr/local/bin/rcpmctl, and leaves everything stopped and
disabled. It does not alter firewall, SSH, package-manager or outbound-network
settings. Failed installation may require inspecting staged/published files;
it never overlays an existing board. Root controls /etc/rcpm/service.conf.

    sudo systemctl start rcpm
    sudo -u rcpm rcpmctl status
    sudo -u rcpm rcpmctl health
    sudo -u rcpm rcpmctl attach

Ctrl-] detaches without stopping the guest. Console history is not replayed or
written to the journal because it may contain private mail or passwords.
Authenticated attachment preserves the shared local sysop console, including
BYE's local blanking controls. Detach before automated stop/backup.

The caller listener defaults to 127.0.0.1:4000. tcpser's caller endpoint is
127.0.0.1:24000; IP232 is 127.0.0.1:25232. Keep both internal ports private.
Local processes are part of the trusted host boundary. RCP/M runs in IP232
mode irrespective of the interactive RCPM.CONF setting. Only change
CALLER_ADDRESS to 0.0.0.0 after qualification and firewall configuration.
Raw caller traffic is plaintext; host administration remains through SSH.

The supervisor gates admission to one caller, drains that connection before
requesting BYE's idle menu, verifies fresh local prompts and invokes
SYSUTLS:BYEBYE. It never injects the shutdown command without acknowledgements.
A caller/attached operator/shutdown timeout leaves the guest running and new
calls disabled. A subsequent explicit stop retries; inspect status, attach to repair locally, return to BYE, and use
`rcpmctl resume` to reopen admission. Resume requires a fresh Hayes initialization
acknowledgement after a shutdown attempt. Forced termination cannot create a verified
backup. Unexpected guest/tcpser failure exits unsuccessfully, allowing systemd
to restart the pair; this is crash recovery, not a clean database shutdown.
KillMode=mixed directs the initial termination signal to the supervisor;
SendSIGKILL=no prevents a timed-out systemd stop from silently killing the guest.
RuntimeDirectoryPreserve=yes keeps the private control socket reachable if a
stop times out while the guest is still running. Check the unit Result and
rcpmctl health after a stop; systemctl stop can return zero even when Result
is timeout and processes are deliberately left alive.
The VPS provider may still hard-power-off the machine.

Linux children arm a parent-death signal before executing the emulator/modem.
If the supervisor is abruptly killed, both children terminate and release
ports/locks so systemd can restart the pair. This is crash cleanup, not a
guarantee that pending CP/M database writes survive. ExecStop is idempotent
after a completed snapshot: a missing control socket is accepted only after
the guest disk lock is free, avoiding false unit failures and unwanted restarts.

## Back up and restore

    sudo -u rcpm rcpmctl backup --output /var/backups/rcpm/snapshot-manual
    sudo systemctl start rcpm
    sudo -u rcpm rcpmctl verify /var/backups/rcpm/snapshot-manual
    sudo -u rcpm rcpmctl restore /var/backups/rcpm/snapshot-manual \
      --output /var/lib/rcpm/restored-instance

A backup stops the guest and keeps the service lease while acquiring the guest
lock, copying sparsely, checking every checksum and atomically publishing a new
snapshot. A manual launch racing the snapshot causes refusal, not a live copy.
Symlinks and special files are rejected. A failed snapshot never replaces an
old one. Failed backups leave the service stopped for inspection; they do not
claim success or silently resume. Restore requires a new directory and does
not automatically change the service target. Preserve credential and disk files
together; do not overlay fresh release images onto accounts/messages.

After a successful restore drill and native qualification:

    sudo systemctl enable rcpm
    sudo systemctl enable --now rcpm-backup.timer

The backup job runs as the unprivileged rcpm account; only its fixed systemctl
restart command runs as root. The optional timer runs at 03:00 host-local time, stops for a verified backup,
and restarts only on success. A persistent missed timer may run at next boot.
It provides local snapshots only: configure off-host copying, retention, upload
storage limits and disk/inode alerts separately. Do not delete snapshots until
an off-host copy is verified. Budget enough free space for a whole snapshot.

## Modem/outbound readiness

Real-tcpser device tests exercise inbound answer, outbound ATD to a loopback
fixture, all 256 byte values, carrier, DTR hangup and inbound recovery. No hub,
mail utility or mail protocol is built. tcpser polls DTR every 100 ms; allow
at least 250 ms of stable DTR high before dialing and stable low on hangup.
The bundled tcpser patch restores command mode and on-hook state after a refused
ATD; without it the next command is swallowed. The patch and complete source are
recorded in the kit. Guest and device probes use loopback only.

A future CPMNet utility must reserve the idle line and disable answering before
dialing. The current service does not schedule outbound calls. Never expose a
caller-accessible general dialer. The disposable guest probe is test media only.

## Remaining release gates

Run native package and service tests on the selected Debian VPS architecture;
verify SSH detach, systemd reboot startup, service restrictions and stop-timeout
behavior; perform an off-host restore; measure resources and complete a 72-hour soak.
The [installed-service caller regression](debian-caller-regression.md) passed
the local Debian ARM64 BYE/AUTH, XMODEM/YMODEM and CHAT checks through IP232.
The rc2 service kits incorporate the recorded helper fix. Repeat applicable
acceptance checks on the intended deployment architecture.
Disposable VM tests cover real systemd and reboot behavior; they do not
establish active-write power-loss consistency or public-network resilience. Keep 4 MHz until timing-sensitive behavior is qualified.

## Repeat local qualification

From the source checkout (or source/host-linux in the kit):

    RCPM_TEST_TCPSER=/path/to/runtime/tcpser python3 -m unittest \
      test_modem_device test_native_service
    python3 check_native_service.py /path/to/extracted/RCPM-linux-arm64

The second command copies the entire installation to temporary directories;
allow roughly 2 GiB of temporary disk space. It does not install service units,
modify the supplied package, or publish ports beyond loopback. Diagnostic console
traces stay in the disposable fixture and are removed with it.

For actual guest dialing, build z80asm from the bundled z80pack source in a
separate build directory, then run:

    python3 check_outbound_modem.py --source /path/to/z80pack \
      --runtime /path/to/runtime/cpmsim --cpmcp /path/to/runtime/cpmcp \
      --tcpser /path/to/runtime/tcpser

DIALPRB is a disposable test program, not a CPMNet implementation or public
caller utility. It dials only the loopback fixture supplied by the harness,
echoes 1024 bytes spanning all byte values, drops DTR and returns to CP/M.

`health` returns a failure exit status while starting, draining or stopped. It
confirms the Hayes startup acknowledgement and live processes, not continued
CP/M responsiveness after arbitrary guest failure. It never takes the caller
line. End-to-end responsiveness must be checked during an idle maintenance window.

The complete-board outbound check additionally installs DIALPRB only on a
disposable private disk, leaves BYE locally, dials the fixture, returns to BYE
and verifies a subsequent inbound HELP session:

    python3 check_board_outbound.py /path/to/extracted/RCPM-linux-arm64 \
      --probe /path/to/assembled/dialprobe.bin

The service qualification also terminates only its own disposable tcpser child,
requires the supervisor to report failure, and starts the pair again to verify
caller access and credential preservation. This is not a crash-consistency proof.

The bundled tcpser also fixes its control-pipe batch loop to handle each event
in order. Upstream repeatedly handles the first byte, potentially losing a
DTR-down event queued with DTR-up. Both changes are listed in TCPSER.json.
