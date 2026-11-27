# Optional hosting add-on — local monitoring

This feature belongs only to the separate Linux hosting add-on, not the
standard RCP/M package or published v1.2.2-rc2 kits. It adds local operator alerts and an optional real
caller responsiveness check. They do not deliver email/webhook notifications.

## Enable and inspect

After installing a kit containing these units:

```sh
sudo systemctl enable --now rcpm-monitor.timer
sudo journalctl -t rcpm-monitor -p err
sudo -u rcpm rcpmctl alerts
sudo -u rcpm rcpmctl health --probe
```

The timer checks every five minutes (first check two minutes after boot), covering
systemd state, automatic restart counts, free
space and free inodes, and attempts an idle-line HELP probe. The shipped
OnFailure hooks also record RCP/M and backup unit failures immediately.
Alerts and recoveries appear in the journal with error/notice priorities.
`rcpmctl alerts` reads the private, atomic status file, even when the board is
stopped. It retains at most 100 transition events; unchanged problems are not
repeated in that event history.

Only the timer is opt-in. The installer leaves it stopped and disabled along
with the other timers/services. The existing service restart policy is retained;
the monitor itself never restarts, stops, unblanks or writes to the CP/M console.

## What the probe establishes

The supervisor reserves an idle modem line, connects through private tcpser,
waits for the caller CP/M prompt, sends HELP, checks its response and waits for
fresh BYE carrier-loss cleanup. It uses no credentials or operator keyboard
injection. Success establishes one completed caller transaction at that time.

The probe defers when a caller is connected, an operator is attached, another
private operation holds the service lease, shutdown is draining, or fewer than
10 seconds have passed since the last caller/probe. Backup maintenance is also
excluded. A deferred result is explicitly reported; it does not establish guest
responsiveness. An active caller or operator is not interrupted.

During an actual idle probe, new callers are briefly rejected. A healthy probe
can take several seconds; the default deadline is 30 seconds. Monitoring cadence
therefore trades off failure-detection delay against brief idle-line reservations.
`health` without `--probe` retains its process/startup-readiness meaning; status
also includes the most recent executed probe result. Monitoring does not prove
application-level responsiveness during a long active caller session.

## Storage and restart policy

Defaults are 512 MiB available space, five percent available blocks, 1,024 free
inodes, and three automatic restarts observed within ten minutes. A lifetime
restart counter alone is not treated as a recent loop; samples reset when the
counter resets or older observations expire. The data and backup paths are
checked separately, even when they reside on different filesystems.

Optional root-managed `/etc/rcpm/monitor.json` can override thresholds:

```json
{
  "min_free_bytes": 536870912,
  "min_free_percent": 5,
  "min_free_inodes": 1024,
  "restart_window": 600,
  "restart_limit": 3,
  "probe_timeout": 30
}
```

Use root ownership, group `rcpm` and mode 0640. `data_path` and `backup_path`
may override the default `/var/lib/rcpm` and `/var/backups/rcpm` paths.
Status/events live under `/var/lib/rcpm/monitor`, privately owned by `rcpm`.
No console output, caller data, passwords or mail are included in alert records.
The periodic checker and failure hook serialize their state writes so one
cannot discard the other's alert while a probe is in progress.

## Responding to alerts

Resolve the storage or backup problem and verify the last good snapshot before
restarting a board stopped by a failed backup. Do not treat an interrupted
staging directory as a published snapshot. The monitor records recovery after
subsequent successful checks; a failed backup remains visible through systemd
Result until reset or a successful retry. Recent restart-loop evidence remains
visible until its observation window expires.

An unresponsive guest alert requires operator investigation. The checker leaves
the guest running rather than discarding its state. An unavailable private
supervisor control socket is bounded by the probe budget plus five seconds.
External notification delivery, off-host recovery, long-duration resource
measurements and public-network acceptance remain separate qualification work.
