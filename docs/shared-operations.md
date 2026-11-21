# Shared RCP/M operation

`launch_rcpm.zsh` defaults to `build/upper-system-final`, tmux session
`rcpm-shared` and raw TCP **127.0.0.1:4002**. One cpmsim process supplies both
the caller connection and the local console. No separate listener or disk
publication is needed. The listener remains loopback-only.

## Start and attach

Run `rcpm`, or the installation's `Start-RCPM.command`. Both start the guest
when stopped and attach to its console when already managed by this launcher.
Detach with **Ctrl-B D**; the guest and listener continue running. Run the same
command again to reattach. To send BYE a literal Ctrl-B, press **Ctrl-B Ctrl-B**.

The first transition requires stopping the existing manually launched guest:
save work, let the caller disconnect, obtain local CP/M and enter
`SYSUTLS:BYEBYE`. Then run `rcpm`. A running console cannot be moved into the new
tmux session automatically. The launcher refuses a second process on the same
installation, a conflicting port or a session belonging to another installation.
It never kills the earlier `rcpm-console` or `rcpm-listener` sessions.

The user's original `~/scripts/rcpm` wrapper does not forward arguments.
A replacement is supplied at `host/rcpm`. Install it once from the repository:

```sh
cp host/rcpm "$HOME/scripts/rcpm"
```

The existing wrapper already launches the new default system without options.
The replacement adds option forwarding; it does not change shell/tmux settings.
The development workspace cannot write directly into `~/scripts`.

## Stop and back up

`BYE` logs off the caller. `SYSUTLS:BYEBYE` in local private CP/M stops the guest.
Detaching from tmux does not stop it. Save application work before shutdown.

After stopping, run either `rcpm --backup` or `Backup-RCPM.command` in the
installation directory. Backups go into the repository's `build/backups/` with
a UTC timestamp, or specify an explicit destination:

```sh
rcpm --backup /path/to/rcpm-backup
rcpm --verify-backup /path/to/rcpm-backup
rcpm
```

Backups refuse a running guest. They hold the same instance lock while copying
and verify every copied file against a SHA256 manifest before publishing the
backup. Copies include A:/I:/J:/P:, runtime, configuration, mounted volume
collection, offline media, submitted uploads and private RBBS credentials.
Zero-filled archive ranges stay sparse. Credentials retain their file
permissions; the payload directory is private. Historical rollback `backups/`
and transient locks are excluded. Keep an additional copy on separate storage:
`build/backups` on the same disk is recovery convenience, not protection against
loss of that disk. Restore uses the backup as a complete snapshot; do not merge
later uploads from an abandoned installation blindly.

## Restore

Restore only to a new directory. Existing installations are never overwritten:

```sh
rcpm --restore /path/to/rcpm-backup --output /path/to/restored-rcpm
/path/to/restored-rcpm/Start-RCPM.command
```

All backed-up files are checked before restoration. Disk images, uploads,
RBBS data and credentials are copied unchanged. Host `.command` helpers are
rebound to the new installation path; obsolete rollback references are removed.
The restored runtime must be compatible with the host. Helpers still depend on
this repository's Python scripts and tools; this is an installation snapshot,
not a standalone redistributable release. Keep the repository with the backup.

Stop the original guest before starting a restored copy on its port. To make
the restored installation the normal `rcpm` target, set `RCPM_INSTANCE` to its
absolute directory in your shell configuration. Optional `RCPM_PORT` and
`RCPM_SESSION` select a different port/session; keep them consistent when
reattaching. `rcpm --check` validates paths and reports the guest lock state.

## Verification and limits

`check_shared_operations.py` checks populated disk/data hashes, sparse archive
copying, inbox restoration, credential permissions, corrupt/path-traversal and
existing-target refusal, live-instance lock refusal, a restored guest boot and
caller login. Session-adapter checks cover reuse, foreign ownership, duplicate
guests and occupied ports. Actual tmux create/attach/switch could not be tested
in the development sandbox, which denies tmux server access. On the host, check
one launch, detach, reattach and caller connection before relying on background
operation.

The earlier separate-instance workflow remains at `launch_legacy_rcpm.zsh`.
Its publishing and service-management options do not apply to this installation.
