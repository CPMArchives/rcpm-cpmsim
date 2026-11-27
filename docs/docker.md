# Docker packages

## GHCR images

The repository's `Publish released Docker images to GHCR` workflow publishes
the Docker archives attached to a release after verifying their SHA256SUMS.
One image tag supports both Linux ARM64 and x64; Docker selects the host
architecture. The registry image adds identification labels only; it retains
the released image filesystem. The archive downloads remain available.

The public [GHCR package](https://github.com/CPMArchives/rcpm-cpmsim/pkgs/container/rcpm-cpmsim)
is available without signing in. Installation is:

```sh
docker pull ghcr.io/cpmarchives/rcpm-cpmsim:1.2.1
docker run --name rcpm -it -p 127.0.0.1:4000:4000 \
  -v rcpm-data:/data ghcr.io/cpmarchives/rcpm-cpmsim:1.2.1
```

New published releases containing both Docker archives and checksums trigger
publication automatically. Version tags remain available. `latest` follows
GitHub's current stable release, never a prerelease or an older manual replay.
A release without Docker assets leaves GHCR unchanged. If assets are added
after a release is published, run the workflow manually with its release tag.
The workflow uses GitHub's built-in token; no Docker Hub account or additional
publishing secret is required. Initial GHCR package visibility must be public
for anonymous pulls (GitHub defaults new packages to private).

This updates the registry, not running boards. Existing containers and data
volumes are unchanged. Upgrade an existing board separately; pulling an image
does not migrate the initialized installation in its persistent volume.

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

Generally, you should not need to change the container's internal port.
If you want to change it, change the second **port number** in the mapping
(`HOST_PORT:CONTAINER_PORT`) and set `--port` to match. For example, to use
port 5000 both externally and internally:

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

## MULTIPLE INSTANCES

You can run multiple independent RCP/M systems on the same computer. Give each
instance a unique container name, an unused host port, and its own data volume.
Each instance supports one caller at a time and has its own sysop console,
credentials, disks, caller data and uploads. Never share a data volume between
running instances.

Start the first instance in one terminal:

```sh
docker run --name rcpm-one -it \
  -p 127.0.0.1:4000:4000 \
  -v rcpm-one-data:/data \
  cpmarchives/rcpm:1.2.1-arm64
```

Start the second instance in another terminal:

```sh
docker run --name rcpm-two -it \
  -p 127.0.0.1:5000:5000 \
  -v rcpm-two-data:/data \
  cpmarchives/rcpm:1.2.1-arm64 --port 5000
```

For x64, use `cpmarchives/rcpm:1.2.1-x64` in both commands.
Wait for each instance's ready message, then connect raw TCP callers to
`127.0.0.1:4000` and `127.0.0.1:5000`, respectively. These examples publish
only on your computer's loopback address. Each startup reports its own
internal listening port, matching the host port in these examples.

Detach from either sysop console with Ctrl-P, Ctrl-Q. Reattach using
`docker attach rcpm-one` or `docker attach rcpm-two`. After a clean shutdown,
restart an existing container with `docker start -ai rcpm-one` or
`docker start -ai rcpm-two`. Reuse each instance's original volume when
recreating its container; keep the volumes separate and back them up while
the corresponding RCP/M system is stopped.

### Simultaneous-instance validation

Both released Docker packages (ARM64 and x64) passed a two-instance test on
26 November 2026. Two callers connected simultaneously to ports 4000 and 5000.
One caller entered RBBS while the other used CP/M HELP. Each instance reported
its correct startup port and used a separate data volume and independently
generated credentials. After the first instance shut down, the second caller
remained connected and successfully used HELP again. Both shut down cleanly.

These checks used ports 4000 and 5000 inside an isolated Docker network because
the host ports were occupied; simultaneous publication of those host ports was
not tested in this pass. The x64 package ran under QEMU CPU emulation on an
ARM64 host; native x64 hardware was not tested. Results and tested archive
hashes are recorded in the [validation report](https://github.com/CPMArchives/rcpm-cpmsim/blob/main/docs/performance/LINUX-DOCKER-VALIDATION.json),
also attached to the release as `LINUX-DOCKER-VALIDATION.json`.

### Mixed ARM64 and x64 validation

A mixed pair also passed on 26 November 2026: one released ARM64 instance on
port 4000 and one released x64 instance on port 5000, running simultaneously
with separate data volumes and independent credentials. Both callers logged
in; the ARM64 caller entered RBBS while the x64 caller used CP/M HELP.
After the ARM64 instance shut down, the x64 caller remained connected and
successfully used HELP again. Both instances reported their correct startup
ports and shut down cleanly.

This test used ports 4000 and 5000 inside an isolated Docker network, without
publishing the occupied host ports. ARM64 ran natively and x64 ran under QEMU
CPU emulation on the ARM64 Docker host. See the linked validation report above
for results and tested archive hashes.

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
