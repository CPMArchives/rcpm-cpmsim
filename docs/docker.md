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

### Change the port

Docker port mappings use `HOST_ADDRESS:HOST_PORT:CONTAINER_PORT`. To accept
connections on host port 5000 while keeping RCP/M's internal port at 4000,
replace `-p 127.0.0.1:4000:4000` with `-p 127.0.0.1:5000:4000` in the startup
command. Connect your terminal to `127.0.0.1:5000`. Startup still reports 4000,
because it reports the internal listening port.

To use port 5000 both inside and outside the container, run:

```sh
docker run --name rcpm -it \
  -p 127.0.0.1:5000:5000 \
  -v rcpm-data:/data \
  cpmarchives/rcpm:1.2.1-arm64 --port 5000
```

For x64, replace the image tag with `cpmarchives/rcpm:1.2.1-x64`.
The `--port 5000` option must follow the image name. Startup then reports
`RCP/M is now running on port 5000.`; connect to `127.0.0.1:5000`.
Choose an unused host port.

Port mappings are set when creating a container. If a container named `rcpm`
already exists, shut down RCP/M cleanly, remove the stopped container with
`docker rm rcpm`, and recreate it using the revised command and the same
`rcpm-data` volume. Keep the volume to preserve your installation.

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
then finalize it with `finalize_linux_release.py`.

Before running the commands below:

- Run from the repository root in Bash on Linux or macOS, with Python 3,
  Docker Engine (or Docker Desktop), and the Docker Buildx plugin available.
  The checker does not run directly in native Windows Python; use a Linux
  environment such as WSL with Docker integration instead.
- The matching finalized Linux package must already exist at
  `build/publish-linux/RCPM-linux-arm64` or
  `build/publish-linux/RCPM-linux-x64`. The Dockerfile copies those existing
  binaries; selecting a platform does not compile or convert them.
- When building or checking an architecture different from your Docker host,
  configure support for running that architecture, such as CPU emulation.
- Each check output directory must be new. For a repeat run, choose another
  `--output` path rather than overwriting an earlier report.
- Run the ARM64 and x64 checks sequentially, with host port `14000` free.
  Both checks use that port.
- Each Bash block enables `set -euo pipefail` so a failed build, check, or
  image export stops the sequence, including failures within the gzip pipeline.

The explicit platform selects the image architecture; the tag alone does not.
Docker calls x64 `amd64`. `--load` loads each image into the local Docker image
store so the checker and `docker save` can use it.

### ARM64

```bash
set -euo pipefail

docker buildx build --platform linux/arm64 --load \
  --build-arg PACKAGE=build/publish-linux/RCPM-linux-arm64 \
  -f packaging/docker/Dockerfile -t cpmarchives/rcpm:1.2.1-arm64 .
python3 check_docker_release.py cpmarchives/rcpm:1.2.1-arm64 \
  --output build/docker-check-arm64
docker save cpmarchives/rcpm:1.2.1-arm64 | gzip > rcpm-v1.2.1-docker-arm64.tar.gz
```

### X64

```bash
set -euo pipefail

docker buildx build --platform linux/amd64 --load \
  --build-arg PACKAGE=build/publish-linux/RCPM-linux-x64 \
  -f packaging/docker/Dockerfile -t cpmarchives/rcpm:1.2.1-x64 .
python3 check_docker_release.py cpmarchives/rcpm:1.2.1-x64 \
  --output build/docker-check-x64
docker save cpmarchives/rcpm:1.2.1-x64 | gzip > rcpm-v1.2.1-docker-x64.tar.gz
```

Release validation reports describe the tested environments. IP232 and native x64 hardware are outside this qualification pass. All inherited component terms and notices remain applicable; the Docker wrapper does not change them.
