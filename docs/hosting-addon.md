# Optional RCP/M administration add-on 0.1.0

RCP/M's standard package is self-contained: unpack it where you want, run its
launcher, edit the small host connection configuration and board configuration,
then shut down and restart. Local use and hosted use share that workflow.
The standard package neither installs nor depends on system services, scheduled
backups, monitoring, alert state or this add-on. Its internal caller permissions
and clean shutdown remain part of the base system.

The optional hosting add-on provides systemd supervision, a reattachable private
console, verified backup/restore commands, an optional daily backup timer and
local monitoring. Its separate administration instructions are for operators
who deliberately choose host integration. Monitoring records local alerts; it
does not deliver remote notifications. Probes briefly reserve an idle caller line.

## Downloads and platform scope

This add-on is versioned independently and requires the published RCP/M 1.2.2
standard Linux package. Historical v1.2.2 service prereleases are combined kits,
not this supplemental download. Existing boards are not migrated automatically.

| Platform | Standard workflow | Hosting add-on |
| --- | --- | --- |
| macOS ARM64 | Platform launcher | None supplied |
| Windows x64 / ARM64 | Platform launcher, where a matching build is available | None supplied |
| Linux x64 / ARM64 | `Start-RCPM.sh` | Debian/systemd add-on |
| Docker | Container entry point | None supplied; host orchestration is separate |

This split does not claim new builds or qualification for other platforms.
For Linux, choose the matching pair:

- `rcpm-v1.2.2-linux-arm64.tar.gz` and, optionally, `rcpm-admin-v0.1.0-linux-arm64.tar.gz`
- `rcpm-v1.2.2-linux-x64.tar.gz` and, optionally, `rcpm-admin-v0.1.0-linux-x64.tar.gz`

The add-on contains no board disk images or duplicate emulator. Extract it into
its own directory beside a freshly unpacked matching standard package. Do not
extract it over a board. Do not install from a running or personalized board:
existing accounts/messages are not migrated by this installer.

```sh
cd RCPM-admin-linux-arm64
./Install-Hosting.sh --package ../RCPM-linux-arm64 --check
sudo ./Install-Hosting.sh --package ../RCPM-linux-arm64 --install
```

Preflight verifies add-on files, base manifests and compatible runtime/media.
Installation copies the pristine standard board to `/var/lib/rcpm/instance`;
the original package is unchanged. Services and timers remain stopped/disabled,
with caller access restricted to loopback. The installed board subsequently
has its own data: do not operate the original as if it were the same board.

Continue with [hosting administration](INSTALLATION-NATIVE-SERVICE.md).
These procedures are not part of the common sysop manual. Ordinary users need
neither this add-on nor Python/systemd to use the standard foreground launcher.

## Packaging and maintenance

Build this supplemental archive from an exact standard package:

```sh
python3 build_admin_addon.py --package rcpm-v1.2.2-linux-arm64.tar.gz \
  --output build/admin-arm64
```

The add-on has its own manifest and pins the compatible base runtime/media
hashes. It contains no emulator, modem binary or board disk images. Its
administration guide and checksums accompany its own release. No additional
macOS, Windows or Docker administration layer is supplied by this add-on.
