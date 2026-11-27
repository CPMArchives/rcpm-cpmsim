#!/usr/bin/env python3
"""Publish checksum-verified release Docker archives; never build unreleased code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


def run(*args, capture=False):
    return subprocess.check_output(args, text=True).strip() if capture else subprocess.run(args, check=True)


def api(repository, suffix):
    return json.loads(run('gh', 'api', 'repos/' + repository + '/' + suffix, capture=True))


def archive_identity(path, architecture):
    with tarfile.open(path) as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        if len(manifest) != 1 or len(manifest[0].get('RepoTags', [])) != 1:
            raise ValueError('Expected exactly one tagged Docker image')
        config = json.load(archive.extractfile(manifest[0]['Config']))
    if config.get('os') != 'linux' or config.get('architecture') != architecture:
        raise ValueError('Unexpected image platform')
    tag = manifest[0]['RepoTags'][0]
    if not re.fullmatch(r'[a-z0-9./:_-]+', tag):
        raise ValueError('Invalid saved image name')
    return tag


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def publish(repository, tag):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', tag):
        raise ValueError('Expected a version release tag')
    release = api(repository, 'releases/tags/' + tag)
    if release['draft']:
        raise ValueError('Refusing to publish a draft release')
    version = tag[1:]
    image = 'ghcr.io/' + repository.lower()
    names = ['rcpm-' + tag + '-docker-' + arch + '.tar.gz' for arch in ('arm64', 'x64')]
    available = {a['name'] for a in release['assets']}
    if not set(names + ['SHA256SUMS']) <= available:
        if __import__('os').environ.get('GITHUB_EVENT_NAME') == 'release':
            print('Release has no complete Docker archive pair; GHCR unchanged.')
            return
        raise ValueError('Release needs both Docker archives and SHA256SUMS')
    commit = api(repository, 'commits/' + tag)['sha']
    with tempfile.TemporaryDirectory(prefix='rcpm-registry-') as temporary:
        folder = Path(temporary)
        run('gh', 'release', 'download', tag, '--repo', repository, '--dir', str(folder),
            '--pattern', 'SHA256SUMS', '--pattern', 'rcpm-' + tag + '-docker-*.tar.gz')
        checksums = {}
        for line in (folder / 'SHA256SUMS').read_text().splitlines():
            parts = line.split()
            if len(parts) == 2:
                checksums[parts[1].lstrip('*')] = parts[0]
        # Validate BOTH before publishing either architecture.
        sources = []
        for name, architecture in zip(names, ('arm64', 'amd64')):
            path = folder / name
            if checksums.get(name) != digest(path):
                raise ValueError('Release checksum mismatch: ' + name)
            sources.append(archive_identity(path, architecture))
        tags = []
        for name, source, architecture in zip(names, sources, ('arm64', 'amd64')):
            target = image + ':' + version + '-' + architecture
            run('docker', 'load', '--input', str(folder / name))
            run('docker', 'build', '--builder', 'default', '--platform', 'linux/' + architecture,
                '--build-arg', 'RELEASE_IMAGE=' + source,
                '--label', 'org.opencontainers.image.source=https://github.com/' + repository,
                '--label', 'org.opencontainers.image.version=' + version,
                '--label', 'org.opencontainers.image.revision=' + commit,
                '--file', 'packaging/docker/registry.Dockerfile', '--tag', target, '.')
            run('docker', 'push', target)
            tags.append(target)
        run('docker', 'buildx', 'imagetools', 'create', '--tag', image + ':' + version, *tags)
        # Only the current stable release may move latest, including on manual replays.
        latest = api(repository, 'releases/latest')
        if not release['prerelease'] and latest['tag_name'] == tag:
            run('docker', 'buildx', 'imagetools', 'create', '--tag', image + ':latest', image + ':' + version)
        run('docker', 'buildx', 'imagetools', 'inspect', image + ':' + version)
        summary = __import__('os').environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write('Published `' + image + ':' + version + '` for linux/arm64 and linux/amd64.\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', required=True)
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    publish(a.repository, a.tag)
