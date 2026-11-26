# Docker packages

## CONTENTS

The 1.2.1 release provides Docker image archives for ARM64 and x64. Download
`rcpm-v1.2.1-docker-arm64.tar.gz` or `rcpm-v1.2.1-docker-x64.tar.gz` from
https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.2.1.

## STARTUP

These archives are loaded locally; no registry login or registry image is needed. Assuming you have Docker installed, run:

### ARM64:

```sh
docker load -i rcpm-v1.2.1-docker-arm64.tar.gz
docker run --name rcpm -it -p 127.0.0.1:4000:4000 \
  -v rcpm-data:/data cpmarchives/rcpm:1.2.1-arm64
```

### X64

```sh
docker load -i rcpm-v1.2.1-docker-x64.tar.gz
docker run --name rcpm -it -p 127.0.0.1:4000:4000 \
  -v rcpm-data:/data cpmarchives/rcpm:1.2.1-x64
```

Wait until you see the message `RCP/M modem ready.`. The system is now ready to accept callers.

## CONNECT

You can now connect a raw TCP terminal to `127.0.0.1:4000`.

## SYSOP TERMINAL

The attached Docker terminal is the local sysop console. To detach from the console without closing stdin, press Docker's Ctrl-P, Ctrl-Q sequence; to reattach, run `docker attach rcpm`.

## BACKUP AND UPDATE

Before backing up or updating the system, be sure to stop the RCP/M session. Shut down RCP/M from its console as described in the sysop guide before stopping
or replacing the container. The package requires a terminal (`-it`).

The named volume stores the complete writable installation, including disks,
private SYSOP.DOC, caller data and uploads. Recreating a container with the same
volume preserves that installation; it does not overwrite it with a fresh seed.

Do not remove it to upgrade.

The internal listener uses 0.0.0.0 for Docker forwarding; the example publishes
only on the host's loopback address. Bind a different host address deliberately
if callers should connect from elsewhere. This is raw TCP, not Telnet.

`packaging/docker/compose.yaml` is an optional Compose example. Set its image
to the tag loaded for your architecture before running `docker compose up`.
It enables stdin and a terminal and retains a named volume.

## REBUILD

Build the Linux package using `build_linux_release.py`, run `check_release.py`,
then finalize it with `finalize_linux_release.py`. From the repository root:

### ARM64

```sh
docker build --build-arg PACKAGE=build/publish-linux/RCPM-linux-arm64 \
  -f packaging/docker/Dockerfile -t cpmarchives/rcpm:1.2.1-arm64 .
python3 check_docker_release.py cpmarchives/rcpm:1.2.1-arm64 \
  --output build/docker-check-arm64
docker save cpmarchives/rcpm:1.2.1-arm64 | gzip > rcpm-v1.2.1-docker-arm64.tar.gz
```

### X64

```sh
docker build --build-arg PACKAGE=build/publish-linux/RCPM-linux-x64 \
  -f packaging/docker/Dockerfile -t cpmarchives/rcpm:1.2.1-x64 .
python3 check_docker_release.py cpmarchives/rcpm:1.2.1-x64 \
  --output build/docker-check-x64
docker save cpmarchives/rcpm:1.2.1-x64 | gzip > rcpm-v1.2.1-docker-x64.tar.gz
```

Release validation reports describe the tested environments. IP232 and native x64 hardware are outside this qualification pass. All inherited component terms and notices remain applicable; the Docker wrapper does not change them.
