# RCP/M 1.2.2 — bundled virtual modem

All standard platform packages include tcpser. Defaults require no setup:
unpack and run the normal platform launcher. Direct TCP remains the default
on local address 127.0.0.1, caller port 4000. The commented external RCPM.CONF
explains each setting. Stop RCP/M before editing it and restart afterwards.

Setting MODE=ip232 makes the launcher start the bundled virtual modem and
stop it when CP/M exits. PORT is the caller port in both modes; the private
loopback modem endpoint is chosen automatically. No manual modem command,
system service, installation wizard, timer or monitoring setup is required.

Packages: macOS ARM64, Linux ARM64/x64, Windows x64 (also checked on Windows 11
ARM64 using x64 emulation), and Docker ARM64/x64. The Windows modem includes
its required runtime DLL and corresponding source; no Cygwin installation is
required on the sysop's computer. This does not claim native ARM64 Windows
binaries. Docker retains its normal image, port mapping and persistent-volume
workflow; images are also published to GHCR automatically after release.

Guest disk images, BYE/AUTH, RBBS, CHAT and emulator binaries are retained from
v1.2.1. tcpser includes the recorded failed-dial recovery and batched control-event
fixes. Host launchers, documentation and package metadata are updated.

The optional Linux hosting/administration add-on remains separate. No scheduled
backups, service installer or monitoring components are added to standard
packages. Existing v1.2.1 and historical service prereleases remain unchanged.

Validation covers the changed foreground launch path in direct and bundled-modem
modes: startup, HELP, disconnect/reconnect, clean stop and caller-port release.
Docker also checks caller/RBBS access and preservation across container replacement.
Exact platform results accompany the release. No soak, VPS deployment or CPMNet
implementation is claimed.

Fresh packages are new boards. Do not unpack over a live installation. Retain
complete stopped board data and private credentials when upgrading. A new Docker
image does not automatically migrate an existing initialized data volume.
