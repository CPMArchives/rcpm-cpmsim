# Docker packages

The 1.2.1 release provides Docker image archives for ARM64 and x64. Download
`rcpm-v1.2.1-docker-arm64.tar.gz` or `rcpm-v1.2.1-docker-x64.tar.gz` from
https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.2.1.
These archives are loaded locally; no registry login or registry image is needed.

```sh
docker load -i rcpm-v1.2.1-docker-arm64.tar.gz
docker run --name rcpm -it -p 127.0.0.1:4000:4000 \
  -v rcpm-data:/data cpmarchives/rcpm:1.2.1-arm64
```

For x64 use the `docker-x64` archive and tag `cpmarchives/rcpm:1.2.1-x64`.
After `RCP/M modem ready.`, connect a raw TCP terminal to `127.0.0.1:4000`.
The attached terminal is the local sysop console. To detach without closing
stdin, press Docker's Ctrl-P, Ctrl-Q sequence; use `docker attach rcpm` to return.
Shut down RCP/M from its console as described in the sysop guide before stopping
or replacing the container. The package requires a terminal (`-it`).

The named volume stores the complete writable installation, including disks,
private SYSOP.DOC, caller data and uploads. Recreating a container with the same
volume preserves that installation; it does not overwrite it with a fresh seed.
Back up the volume while RCP/M is stopped. Do not remove it to upgrade.
The internal listener uses 0.0.0.0 for Docker forwarding; the example publishes
only on the host's loopback address. Bind a different host address deliberately
if callers should connect from elsewhere. This is raw TCP, not Telnet.

`packaging/docker/compose.yaml` is an optional Compose example. Set its image
to the tag loaded for your architecture before running `docker compose up`.
It enables stdin and a terminal and retains a named volume.

## Rebuild and qualify

Build the Linux package using `build_linux_release.py`, run `check_release.py`,
then finalize it with `finalize_linux_release.py`. From the repository root:

```sh
docker build --build-arg PACKAGE=build/publish-linux/RCPM-linux-arm64 \
  -f packaging/docker/Dockerfile -t cpmarchives/rcpm:1.2.1-arm64 .
python3 check_docker_release.py cpmarchives/rcpm:1.2.1-arm64 \
  --output build/docker-check-arm64
docker save cpmarchives/rcpm:1.2.1-arm64 | gzip > rcpm-v1.2.1-docker-arm64.tar.gz
```

Use the matching build platform and Linux package for x64. Release validation
reports describe the tested environments. IP232 and native x64 hardware are
outside this qualification pass. All inherited component terms and notices
remain applicable; the Docker wrapper does not change them.
