#!/bin/sh
# Explicit local installation only. Never invoked by a build or test.
set -eu
service_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
cd -P "${RCPM_PACKAGE_ROOT:-$service_dir/..}"
case "${1:---check}" in
  --check|--install) ;;
  *) echo 'Usage: sudo ./service/Install-Service.sh --install (or --check)' >&2; exit 2 ;;
esac
[ "$(uname -s)" = Linux ] || { echo 'Linux required' >&2; exit 1; }
command -v systemctl >/dev/null
[ -d /run/systemd/system ] || { echo 'A running systemd host is required' >&2; exit 1; }
command -v python3 >/dev/null
python3 -c 'import sys; assert sys.version_info >= (3,9), "Python 3.9+ required"'
[ -x runtime/tcpser ] || { echo 'Use a service kit containing the pinned native tcpser binary' >&2; exit 1; }
./runtime/rcpm --check
python3 "$service_dir/preflight.py" .
if [ "${1:---check}" = --check ]; then
  echo 'Preflight passed. No files installed or services started.'; exit 0
fi
[ "$(id -u)" = 0 ] || { echo 'Run --install as root' >&2; exit 1; }
[ ! -e /var/lib/rcpm/instance ] || { echo 'Existing installation refused; preserve its data and use the upgrade procedure' >&2; exit 1; }
[ ! -e /etc/rcpm/service.conf ] || { echo 'Existing configuration refused' >&2; exit 1; }
[ ! -e /etc/systemd/system/rcpm.service ] || { echo 'Existing service refused' >&2; exit 1; }
for target in /usr/local/bin/rcpmctl /usr/local/lib/rcpm /etc/systemd/system/rcpm-backup.service /etc/systemd/system/rcpm-backup.timer /etc/systemd/system/rcpm-monitor.service /etc/systemd/system/rcpm-monitor.timer /etc/systemd/system/rcpm-alert@.service; do
  [ ! -e "$target" ] || { echo "Existing installation path refused: $target" >&2; exit 1; }
done
if ! id rcpm >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/rcpm --shell /usr/sbin/nologin rcpm
fi
install -d -m 0700 -o rcpm -g rcpm /var/lib/rcpm /var/backups/rcpm
install -d -m 0700 -o rcpm -g rcpm /var/lib/rcpm/monitor
install -d -m 0750 -o root -g rcpm /etc/rcpm
# Stage before publishing; service installation never overlays an active board.
stage=$(mktemp -d /var/lib/rcpm/.install.XXXXXX)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
cp -a . "$stage/instance"
chown -R rcpm:rcpm "$stage/instance"
chmod 0700 "$stage/instance"
mv "$stage/instance" /var/lib/rcpm/instance
install -m 0640 -o root -g rcpm "$service_dir/service.conf" /etc/rcpm/service.conf
install -d -m 0755 -o root -g root /usr/local/lib/rcpm
install -m 0644 -o root -g root "$service_dir/rcpm_service.py" /usr/local/lib/rcpm/rcpm_service.py
install -m 0644 -o root -g root "$service_dir/rcpm_monitor.py" /usr/local/lib/rcpm/rcpm_monitor.py
install -m 0755 "$service_dir/rcpmctl" /usr/local/bin/rcpmctl
for unit in rcpm.service rcpm-backup.service rcpm-backup.timer rcpm-monitor.service rcpm-monitor.timer rcpm-alert@.service; do
  install -m 0644 "$service_dir/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
echo 'Installed; no services started or enabled.'
echo 'Next: systemctl start rcpm; sudo -u rcpm rcpmctl status'
echo 'Optional boot startup: systemctl enable rcpm; optional daily backup: systemctl enable --now rcpm-backup.timer'
echo 'For local alerts/idle caller probes: systemctl enable --now rcpm-monitor.timer'
echo 'Backups need an independent off-host copy and retention policy.'
