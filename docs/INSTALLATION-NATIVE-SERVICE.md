# Optional Linux hosting add-on — administration

These instructions apply only to the separately downloaded hosting add-on.
The standard RCP/M package runs through Start-RCPM.sh without any of these
steps. This guide is separate from the common sysop manual.

Administration add-on 0.1.0 is for RCP/M 1.2.2 on Linux ARM64/x64 with systemd.
The release validation report records fresh installation and service operation
on both architectures. Earlier Debian 12.15 tests cover the underlying service,
backup and monitoring behavior. No multi-day soak or live VPS deployment is
claimed. Other platforms retain their ordinary foreground launcher workflow.

## Choose and install

Download the matching standard Linux package and optional hosting add-on.
Verify each against its SHA256SUMS. Extract into separate new directories:
RCPM-linux-arm64 and RCPM-admin-linux-arm64 (or their x64 equivalents).
The add-on contains no disk images or emulator; it verifies the matching base.
Requires Debian Linux with running systemd and Python 3.9+. No compiler,
pip dependency or separate tcpser download is required.

Install from a freshly unpacked standard package. Do not launch or personalize
it first; existing boards are not migrated automatically. Neither directory
may be extracted over a live installation.

```sh
cd RCPM-admin-linux-arm64
./Install-Hosting.sh --package ../RCPM-linux-arm64 --check
sudo ./Install-Hosting.sh --package ../RCPM-linux-arm64 --install
```

Preflight is read-only. Installation creates the unprivileged `rcpm` account,
installs data under `/var/lib/rcpm/instance`, root-owned control helpers under
`/usr/local/lib/rcpm`, configuration under `/etc/rcpm`, and systemd units.
It leaves services **stopped and disabled**, with application access on
**loopback only**. It changes neither SSH nor firewall settings.

Start and inspect the local installation deliberately:

```sh
sudo systemctl start rcpm
sudo -u rcpm rcpmctl status
sudo -u rcpm rcpmctl health
sudo -u rcpm rcpmctl attach
```

Ctrl-] detaches without stopping the board. The public-facing caller listener
is initially `127.0.0.1:4000`; tcpser's internal caller port is
`127.0.0.1:24000` and IP232 is `127.0.0.1:25232`. Keep internal endpoints private.
Service mode selects tcpser/IP232 regardless of the interactive launch profile.
Raw caller traffic is plaintext. Decide on network access and host containment
before changing `/etc/rcpm/service.conf` or exposing any port.

First boot writes the generated private RBBS credentials to
`/var/lib/rcpm/instance/SYSOP.DOC`. Keep this file and the whole installation
private. `Start-RCPM.sh` remains available for interactive operation, but must
not run concurrently with the managed service against the same disks.

## Stop, back up and restore

```sh
sudo systemctl stop rcpm
sudo systemctl show rcpm -p ActiveState -p Result
```

Stop drains the current caller and rejects new callers. A timeout deliberately
leaves the guest alive and private control available. `systemctl stop` can
return zero even when the unit Result is `timeout`; inspect the result/health.
Resolve the caller/console condition before retrying. Do not treat forced
termination as a database-consistent stop.

To make a verified stopped snapshot, choose a new destination:

```sh
sudo -u rcpm rcpmctl backup --output /var/backups/rcpm/snapshot-manual
sudo systemctl start rcpm
sudo -u rcpm rcpmctl verify /var/backups/rcpm/snapshot-manual
sudo -u rcpm rcpmctl restore /var/backups/rcpm/snapshot-manual \
  --output /var/lib/rcpm/restored-instance
```

The backup leaves the guest stopped. Restore requires a new directory and does
not change the service target automatically. Preserve accounts, disk images,
uploads, state and credentials together. Failed backups preserve the last good
snapshot and remain stopped for inspection. Configure separate-storage copying,
retention and disk/inode monitoring independently.

If desired, enable boot startup or the optional daily stopped-backup timer:

```sh
sudo systemctl enable rcpm
sudo systemctl enable --now rcpm-backup.timer
```

The timer runs at 03:00 host-local time, catches up missed runs and restarts the
board only after a successful snapshot. Installation does not enable it.

## Qualification and limits

Read attached `VM-VALIDATION.json` and `DEBIAN-VM-REPORT.md`, plus
`service/README.md` inside the archive. The VM evidence covers 12 integration
groups and 10 Linux safety tests, including reboot/cold start, idle abrupt VM
reset, each component's failure recovery, timeout safety, backup/restore and
persistent timer catch-up. Production payload identity is recorded in the report.

Still unverified: x64 VM/native x64 hardware; sustained 72-hour operation;
active-write power-loss consistency; off-host disaster recovery; public network
and target-VPS behavior; and a full guest-program/BYE AUTH adversarial rerun.
No VPS was deployed and CPMNet was not started during qualification.

Original component notices and licensing terms remain applicable. Bundled tcpser
includes its pinned original source archive, complete patched source, GPL text
and build receipt. See `source/host-linux/build_native_service_kit.py` for rebuilds.
