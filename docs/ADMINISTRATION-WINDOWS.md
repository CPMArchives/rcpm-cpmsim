# Optional Windows administration add-on 0.1.0

For the standard RCP/M 1.2.2 Windows x64 package, including that package under
Windows 11 ARM64's x64 emulation. This separate add-on supplies a background
board, detachable local sysop console, clean shutdown, verified backups and
restoration, optional login startup, and optional backup and monitoring tasks.

It runs under your Windows account. It is not a Windows system service and
does not run before login or promise continued operation after you sign out.
The computer must remain awake to answer callers. Python 3.9 or newer is
required for this add-on; the ordinary RCP/M package still needs no Python.

## Install

Use an ordinary Command Prompt under the account that will operate the board.
Do not use "Run as administrator". Extract the add-on beside a freshly unpacked,
unmodified Windows 1.2.2 package. This installer does not migrate an existing
board. In the add-on directory:

```bat
Install-Hosting.cmd --package ..\RCPM-windows-x64 --check
Install-Hosting.cmd --package ..\RCPM-windows-x64 --install
```

The wrapper uses the Windows Python launcher, `py -3`. If your Python setup
does not provide `py`, run `python -B Install-Hosting.py` with the same arguments.

Installation makes a private copy in `%LOCALAPPDATA%\RCPMAdmin\instance`.
The source package stays unchanged. The board, login startup and schedules
are initially stopped or disabled. The installed board subsequently has its
own messages, files and credentials; it is separate from the source directory.

Use a local filesystem that supports Windows access controls, such as NTFS.
The installer restricts the administration directory to your account and
SYSTEM. It refuses an existing destination, symbolic links and reparse points.
An optional `--home` chooses another new local directory. Administration and
Python paths cannot contain percent signs or newlines.

## Start, console and stop

From Command Prompt:

```bat
set "ctl=%LOCALAPPDATA%\RCPMAdmin\rcpm-admin.cmd"
call "%ctl%" start
call "%ctl%" status
call "%ctl%" attach
```

Ctrl-] detaches the console while leaving the board running. The hidden worker
owns the emulator and bundled modem. Local administration uses an authenticated,
user-only Windows named pipe; it does not open a TCP control port. Console text
stays in memory and is not written to an administration log.

```bat
call "%ctl%" stop
```

Stop waits for callers and carrier cleanup, then shuts down CP/M cleanly. An
attached sysop console must detach first. If the wait expires, the board stays
running with new calls disabled; inspect the session and retry. `resume` can
reopen admission once the guest has returned to modem-ready state. Do not end
the worker in Task Manager as a substitute for a clean shutdown. Windows Job
Objects clean up its child processes if the worker is lost; that is crash
cleanup and does not establish that disk writes completed.

Service mode uses the bundled modem. Caller access defaults to 127.0.0.1:4000.
While stopped, edit `admin.json` to change `address` and `port`. The internal
`caller_port` and `modem_port` remain loopback-only; all three ports must differ.
The managed profile overrides standalone `RCPM.CONF` transport settings. Caller
access is plaintext. Firewall and Internet hosting policy belong to your host
setup.

## Optional startup and schedules

```bat
call "%ctl%" enable board
call "%ctl%" enable backup
call "%ctl%" enable monitor
```

These register separate tasks for this board in Windows Task Scheduler:

| Job | When it runs |
| --- | --- |
| board | At login under your account; up to three one-minute retries after a worker failure |
| backup | Daily at 03:00 local time while your account is logged on |
| monitor | Every five minutes while your account is logged on |

Enabling a task does not start the board immediately; use `start`. The board
task runs with limited privileges and stores no account password. Missed backup
tasks may be offered at the next suitable logged-on session, but do not rely
on a powered-off or sleeping computer running a job. The add-on does not change
power-management settings.

Use `task-status board`, `task-status backup` or `task-status monitor` to inspect
registration. `disable` with the job name removes that task. Disabling `board`
first stops it cleanly. An active backup or monitor task must finish before
it can be disabled. Task names have a unique `RCPM-` prefix stored in admin.json;
no unrelated task is altered. A Python upgrade that removes the recorded
interpreter requires updating its path and recreating the affected tasks.

## Backup and restore

```bat
call "%ctl%" backup
call "%ctl%" verify "%LOCALAPPDATA%\RCPMAdmin\backups\SNAPSHOT"
call "%ctl%" restore "%LOCALAPPDATA%\RCPMAdmin\backups\SNAPSHOT" --output "%USERPROFILE%\RCPM-recovered"
```

Backup detaches no one: callers must finish and the sysop console must detach.
It shuts the board down cleanly, copies and verifies the complete board, then
starts it again only after success. A failed backup records `backup-status.json`
and requires inspection. No forced shutdown is used to complete a backup.
Restore verifies checksums, requires a new destination and preserves the board's
credentials and data together. It does not retarget the running installation.

Choose your own retention and separate-storage copies. The add-on does not
delete old snapshots or provide off-host storage automatically.

## Monitoring and alerts

```bat
call "%ctl%" health --probe
call "%ctl%" monitor
call "%ctl%" alerts
```

Monitoring checks free storage, the most recent backup result, worker failures
and an idle caller HELP transaction. The probe includes carrier-loss cleanup
and has a maximum 120-second budget. It briefly reserves the idle line, defers
during caller/sysop activity or maintenance, and does not force-restart a hung
guest. `status` checks readiness and process state; it does not by itself prove
continued CP/M responsiveness.

Local alert state and changes are recorded in `monitor\state.json`. Worker
outcome is recorded in `run\state.json`; neither file contains console text,
mail or credentials. No email account or external notification service is
supplied. Optional `monitor.json` can override `min_free_bytes` (default
536870912) and `min_free_percent` (default 5).

To return to standalone operation, disable the three tasks and stop the board,
then copy the entire `instance` directory to your chosen location. Keep its
private SYSOP.DOC, disks, uploads and state together. Preserve the board before
removing the administration directory.
