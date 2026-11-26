# Native Debian service installation — v1.2.2-rc1

This is a **prerelease**, not a production-readiness claim. The complete ARM64
service kit passed installer and lifecycle tests in a disposable Debian 12.15
ARM64 VM running real systemd. The x64 kit contains the same host-service fixes,
but **x64 systemd VM and native x64 hardware testing remain pending**.

These are fresh-installation kits around the unchanged v1.2.1 CP/M guest media.
Do not unpack either archive over an existing board. The installer refuses
existing installations; migration of live accounts/messages is not automatic.
There is no CPMNet implementation or scheduled outbound mail polling.

## Choose and verify the download

- ARM64: `rcpm-v1.2.2-rc1-linux-arm64-service.tar.gz`
- x64: `rcpm-v1.2.2-rc1-linux-x64-service.tar.gz`

Both contain the complete system, bundled IP232-capable tcpser, corresponding
source and service helpers. The separate common archive is not required.
Download `SHA256SUMS` alongside your chosen archive and verify it:

```sh
sha256sum --ignore-missing -c SHA256SUMS
```

Requires matching-architecture Debian Linux, running systemd and Python 3.9+.
No compiler, pip dependencies or tcpser download is needed to install the kit.

## Install a fresh board

Extract the archive into a new directory, enter `RCPM-linux-arm64` or
`RCPM-linux-x64`, and run:

```sh
./Install-Service.sh --check
sudo ./Install-Service.sh --install
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

After your own successful qualification and restore drill, boot startup and the
optional daily stopped-backup timer can be enabled:

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
