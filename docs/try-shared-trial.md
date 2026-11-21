> For the current I13:/I14:/I15: installation and tmux launcher, use
> [shared operations](shared-operations.md). This page describes the earlier
> standalone prototype; its B: and I2: locations do not apply to the upper-area build.

# Try the shared-machine prototype

This is a separate, loopback-only trial. The older installation, listener,
private archive and `rcpm` launcher are unchanged. Caller security configuration
and privileged archive maintenance remain unfinished. The trial contains
sample J: files and an empty 512-MiB P:, not the private archive collection.

## Prepare a new trial

First build the runtime and both BYE variants using the
[shared-service build instructions](shared-services.md). Then, from the
repository root:

```sh
python3 prepare_shared_trial.py --source /absolute/path/to/z80pack \
  --romwbw /absolute/path/to/RomWBW --output ../rcpm-shared-trial
```

The preparer refuses to replace an existing trial, including its uploads.
It builds a fresh Z3PLUS/BYE boot disk from stock media and installs UPLOAD,
MESSAGE, YSEND and MOUNT. Automated regression programs are not installed.
It copies the runtime and creates independent I:, J:, P: and DEMO images.
P0: and P1: are named SIGM and CPMUG but are empty. J:/P: are read-only.
B: is SYSUTILS, with routine maintenance tools; callers are denied ordinary
BDOS access to it. Boot support (including SUBMIT and Z3PLUS.LBR) remains
on A:. Development/build materials are in `offline/BUILD.dsk`, outside the
mount collection. Store that image offsite until required for maintenance.
See [the disk layout and boundary](system-disk-layout.md).
The [caller execution boundary](caller-execution.md) admits only the compiled
A0: program list. GET, PATH, SUBMIT and other boot support tools cannot be
loaded by callers; A: rejects caller file modifications. RCP WHL cannot grant
caller privileges using its default password. Use local private mode for
maintenance. These changes require a newly prepared boot disk and BYE build.

## Start and connect

Run the generated launcher in an interactive macOS Terminal:

```sh
../rcpm-shared-trial/Start-RCPM.command
```

This Terminal is the local console. The same cpmsim process owns the TCP
listener; there is no separate Python listener or caller guest. Wait for
`RCP/M modem ready.`

In SyncTERM, create a trial entry or duplicate the existing local entry:

| Setting | Value |
| --- | --- |
| Address | `127.0.0.1` |
| Connection type | Raw |
| TCP port | `4001` |

Connect, then press Return until the `A0:SYSTEM>` prompt appears. The original
listener on port 4000 can remain running. Both terminals now display one
guest session; local typing assists that same caller.

## Exercises

At the caller prompt:

```text
TYPE J:HELLO.TXT
MOUNT /L
MOUNT DEMO
SIGM:
DIR
SYSTEM:
```

DEMO is an actual disk image in `volumes/DEMO.dsk`. The default J: contains
the same sample files. P: starts empty. `BINARY.BIN` on J: contains 2048
bytes covering all 256 byte values.

For a YMODEM download, enter `YSEND J:HELLO.TXT`, then start YMODEM receive
in SyncTERM. For upload, enter `UPLOAD /Y`, then start a YMODEM send. For
a saved message, run `MESSAGE`, enter a line, then enter `/S` on its own line.
Completed files appear in the trial's host `upload-inbox/` directory and
remain after disconnect. I0: WORK is cleared before calls and after them.

To exercise WORK cleanup, use local private mode (below), then enter
`B:PIP I:TEMP.TXT=J:HELLO.TXT`. Restore caller mode, check `DIR I:`, log off
with `BYE`, reconnect, and check `DIR I:` again. PIP is now private on B:.
Store no work that must survive in I0:.

Local Ctrl-B toggles BYE's private blanking at the command prompt. In tmux,
press Ctrl-B twice to pass one literal Ctrl-B to CP/M. This is not a second
independent application session. Sysop write access to J:/P: is not enabled
in this trial.

## Stop

At the caller prompt, `BYE` ends that call and leaves the machine waiting.
To stop the trial, use the local Terminal after the caller disconnects:
press Ctrl-C to open BYE's menu, press Return for local CP/M, then enter
`B:BYEBYE`. The original Terminal shell returns. Uploads remain on disk.

Older prepared trials retain their old disks and commands. Rebuilding does
not update an active installation. Stop the old console before switching
to a newly prepared trial on the same port; preserve its inbox separately.

The trial launcher holds an instance lock to prevent opening its disks in
two emulator processes. It also checks its TCP port before booting. Running
it again while it is active reports that the trial is already running; the
current tmux background/reattach launcher is documented in
[shared operations](shared-operations.md). An alternative loopback port can be selected with
`python3 run_shared_trial.py --instance ../rcpm-shared-trial --port 4002`.
