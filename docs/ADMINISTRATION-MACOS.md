# Optional macOS administration add-on 0.1.0

For the standard RCP/M 1.2.2 macOS ARM64 package. This is a separate, per-user
launchd installation: private detachable console, clean shutdown, verified
backups/restoration, optional scheduling and local monitoring. It does not
alter the ordinary unpack-and-launch package or require root access.

This is a user agent, not a system boot daemon. Login startup requires your
user session; do not rely on the board continuing after logout. The Mac must
remain awake to answer callers. Power management and system-wide hosting are
outside this add-on. No Linux sandbox or remote email notifications are claimed.

## Install

The add-on requires Python 3.9 or newer. Python is needed only for this optional
layer, not the standard Mac package. The installer records its interpreter's
absolute path so launchd does not depend on your interactive shell's PATH.

Extract the add-on beside a freshly unpacked standard package. Do not launch
or personalize that base first; this installer does not migrate an existing board.
From Terminal:

```sh
cd RCPM-admin-macos-arm64
./Install-Hosting.sh --package ../RCPM-macOS-arm64 --check
./Install-Hosting.sh --package ../RCPM-macOS-arm64 --install
```

Do not use sudo. Installation creates a private copy under
`~/Library/Application Support/RCPMAdmin/instance`. It leaves the board,
login startup and schedules stopped/disabled. The source package is unchanged.
The installed copy subsequently has its own data and credentials; do not
treat the original and installed directories as the same board.

## Start, console and stop

The examples use a short shell variable for the controller's pathname:

```sh
ctl="$HOME/Library/Application Support/RCPMAdmin/rcpm-admin"
"$ctl" start
"$ctl" status
"$ctl" attach
```

Ctrl-] detaches. The board continues running. Stop cleanly with:

```sh
"$ctl" stop
```

Stop waits for callers to leave. A timeout refuses to unload the agent and
leaves the board running with new calls disabled; finish or repair the session,
then retry. `resume` can reopen caller admission after a failed stop when the
board is ready. Do not use launchctl force-removal or close processes as a
substitute for a clean CP/M stop. Forced process loss is crash recovery.

Service mode uses the bundled modem. Caller access defaults to 127.0.0.1:4000.
While stopped, `admin.json` sets the caller address/port and private internal
modem ports. Keep internal ports private. Standalone `RCPM.CONF` settings do not
override this managed profile. Raw caller access is plaintext.

## Optional login startup and schedules

```sh
"$ctl" enable board       # start at user login
"$ctl" enable backup      # daily, 03:00 local time
"$ctl" enable monitor     # every five minutes
```

Use `disable` with the same job name to remove that login agent/schedule.
Disabling `board` stops it cleanly first. An active scheduled job must finish
before it can be disabled. Enabling backup or monitoring alone does not enable
board startup at login. Calendar jobs require a suitable active user session;
missed jobs while the Mac is off are not promised to run after the next boot.

Generated plist files are under the private `jobs` directory. Only explicitly
enabled jobs are copied to `~/Library/LaunchAgents`. Avoid changing generated
plists while running. If a Python upgrade removes the recorded interpreter,
preserve board data and update the wrapper/plists to the replacement interpreter.

## Backups and recovery

```sh
"$ctl" backup
"$ctl" verify "$HOME/Library/Application Support/RCPMAdmin/backups/SNAPSHOT"
"$ctl" restore "$HOME/Library/Application Support/RCPMAdmin/backups/SNAPSHOT" \
  --output "$HOME/RCPM-recovered"
```

A backup requests clean shutdown, verifies a complete snapshot and restarts
the board only on success. Failed backups record an alert and require operator
inspection. Detach the operator console before backing up. Restore requires a
new destination, preserves credentials/data together, and does not retarget an
existing launch agent. Keep separate-storage copies and choose your retention
policy; this add-on does not delete old snapshots automatically.

## Monitoring and logs

```sh
"$ctl" health --probe
"$ctl" monitor
"$ctl" alerts
```

Monitoring checks available storage, backup failures, unsuccessful launchd
exits and an idle caller HELP transaction. It defers probes during caller or
operator activity and backup maintenance. Probes briefly reserve the idle line.
An outstanding guest alert clears after a successful probe or service stop;
an unsuccessful previous process exit may remain visible until a clean exit.
Monitoring records local state and never force-restarts an unresponsive guest.

Private state lives under `monitor`; launchd's operational logs are under
`logs`. Raw private console output is not logged. Neither email delivery nor
an external monitoring account is required or supplied. Optional `monitor.json`
can override storage thresholds and probe timeout. Defaults are 512 MiB,
five percent free, 1,024 free inodes and a 120-second probe budget, including
the caller transaction and carrier-loss cleanup.

To return to standalone use, disable the three jobs, stop the board, and copy
the complete `instance` directory to your chosen location. Keep its private
`SYSOP.DOC`, disks, state and uploads together. Do not delete the administration
home without preserving that board data.
