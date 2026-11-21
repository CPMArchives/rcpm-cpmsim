#!/usr/bin/env python3
"""Update BYE on a stopped trial's boot disk, preserving all data disks."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from caller_policy import digest, policy
from rbbs_entry import PREVIOUS_POLICY, BOARD_SHA256, public_entry
from system_attributes import apply as apply_attributes
from runtime_features import require as require_runtime


def upgrade(instance, builds, tools, enable_rbbs=False, runtime=None):
    if not instance.is_dir():
        raise ValueError('Trial directory does not exist')
    with (instance / '.console.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('The trial is running. Leave RBBS with J, then stop it with the private BYEBYE command first.')
        manifest_file = instance / 'trial-build.json'
        manifest = json.loads(manifest_file.read_text())
        if manifest.get('mode') != 'direct':
            raise ValueError('This updater currently supports direct-TCP trial installations')
        old_policy = manifest.get('caller_policy_sha256')
        if old_policy != digest() and not (enable_rbbs and old_policy == PREVIOUS_POLICY):
            raise ValueError('Installed caller policy differs; prepare an explicit migration instead')
        if old_policy != digest() and policy()['programs'] != [
                'BYE.COM', 'CLS.COM', 'DIR.COM', 'HELP.COM', 'TYPE.COM',
                'MOUNT.COM', 'UPLOAD.COM', 'MESSAGE.COM', 'YSEND.COM', 'RBBS.COM']:
            raise ValueError('This migration may add only RBBS to the previous caller policy')
        if enable_rbbs and not manifest.get('rbbs'):
            raise ValueError('This instance does not contain an installed RBBS evaluation')
        if enable_rbbs and not manifest.get('upper_areas'):
            raise ValueError('Public RBBS admission requires the upper-area I15:RBBS profile first')
        result = json.loads((builds / 'build-result.json').read_text())
        if runtime is not None and result.get('idle_timer_port') != 74:
            raise ValueError('Select a timer-capable BYE build when updating the runtime')
        if result.get('idle_timer_port') == 74:
            runtime = runtime or Path(__file__).resolve().parent / 'build/modem/cpmsim'
            require_runtime(runtime, result)
            if (instance / 'runtime/cpmsim').is_symlink():
                raise ValueError('Expected an owned runtime executable')
        if not all(result.get(key) for key in ('private_i2', 'adapter_relocation_fixed', 'private_b')):
            raise ValueError('BYE build lacks the required directory/relocation protections')
        if result.get('caller_policy_sha256') != digest():
            raise ValueError('Rebuild BYE for the current caller policy')
        if enable_rbbs and not result.get('public_rbbs'):
            raise ValueError('BYE lacks the public RBBS entrypoint boundary')
        for name in ('BYE.COM', 'BYEDRIV.COM'):
            record = next(row for row in result['files'] if row['path'] == 'direct/' + name)
            if hashlib.sha256((builds / 'direct' / name).read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Build file hash mismatch: ' + name)
        image = instance / 'disks/drivea.dsk'
        if image.is_symlink() or not image.is_file():
            raise ValueError('Expected an owned, regular boot image, not a disk symlink')
        with tempfile.TemporaryDirectory(prefix='.bye-upgrade-', dir=instance) as temporary:
            work = Path(temporary)
            staged = work / 'drivea.dsk'
            shutil.copyfile(image, staged)
            if runtime is not None:
                shutil.copy2(runtime, work / 'cpmsim')
                shutil.copy2(runtime.with_name(runtime.name + '.features.json'), work / 'cpmsim.features.json')
            if enable_rbbs:
                user = 15 if manifest.get('upper_areas') else 2
                board = work / 'RBBS37.COM'
                subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(staged),
                                f'{user}:RBBS37.COM', str(board)], check=True)
                if hashlib.sha256(board.read_bytes()).hexdigest() != BOARD_SHA256:
                    raise ValueError('Review the installed RBBS executable before admitting callers')
                entry = work / 'RBBS.COM'
                entry.write_bytes(public_entry(Path(manifest['romwbw']), user))
                old_entry = work / 'previous-RBBS.COM'
                subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(staged),
                                '0:RBBS.COM', str(old_entry)], capture_output=True, check=True)
                if old_entry.exists():
                    if old_entry.read_bytes() != entry.read_bytes():
                        raise ValueError('Refusing to overwrite an unrecognized A0:RBBS.COM')
                    subprocess.run([str(tools / 'cpmrm'), '-f', 'ibm-3740',
                                    str(staged), '0:RBBS.COM'], check=True)
                subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(staged),
                                str(entry), '0:RBBS.COM'], check=True)
                verify_entry = work / 'verify-RBBS.COM'
                subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(staged),
                                '0:RBBS.COM', str(verify_entry)], check=True)
                if verify_entry.read_bytes() != entry.read_bytes():
                    raise ValueError('Public RBBS launcher verification failed')
            targets = [(0, 'BYE.COM'), (0, 'BYEDRIV.COM')]
            if manifest.get('rbbs'):
                targets.append((15 if manifest.get('upper_areas') else 2, 'BYE.COM'))
            for user, name in targets:
                subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                                str(staged), f'{user}:{name}'], check=True)
                subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                                str(staged), str(builds / 'direct' / name), f'{user}:{name}'], check=True)
                extracted = work / f'{user}-{name}'
                subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                                str(staged), f'{user}:{name}', str(extracted)], check=True)
                if extracted.read_bytes() != (builds / 'direct' / name).read_bytes():
                    raise ValueError('Installed file verification failed: ' + name)
            # Save a rollback copy before replacing A:. I:, J:, P: and B: are
            # never opened for writing by this updater.
            if manifest.get('caller_tools'):
                manifest['a0_attributes'] = apply_attributes(staged, tools)
            backups = instance / 'backups'
            backups.mkdir(mode=0o700, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            fd, path = tempfile.mkstemp(prefix=f'drivea-before-bye-update-{stamp}-', suffix='.dsk', dir=backups)
            backup = Path(path)
            with os.fdopen(fd, 'wb') as output, image.open('rb') as source:
                shutil.copyfileobj(source, output)
                output.flush()
                os.fsync(output.fileno())
            manifest.setdefault('hashes', {})['disks/drivea.dsk'] = hashlib.sha256(staged.read_bytes()).hexdigest()
            if runtime is not None:
                runtime_backup = backup.with_suffix('.cpmsim')
                shutil.copy2(instance / 'runtime/cpmsim', runtime_backup)
                manifest['runtime_backup'] = str(runtime_backup.relative_to(instance))
                old_features = instance / 'runtime/cpmsim.features.json'
                if old_features.exists():
                    shutil.copy2(old_features, runtime_backup.with_name(runtime_backup.name + '.features.json'))
                manifest['hashes']['runtime/cpmsim'] = hashlib.sha256((work / 'cpmsim').read_bytes()).hexdigest()
            manifest.update(builds=str(builds), private_i2=True, adapter_relocation_fixed=True,
                            boot_backup=str(backup.relative_to(instance)))
            if enable_rbbs:
                manifest.update(public_rbbs=True, caller_policy_sha256=digest())
            pending_manifest = work / 'trial-build.json'
            pending_manifest.write_text(json.dumps(manifest, indent=2) + '\n')
            with staged.open('r+b') as source:
                os.fsync(source.fileno())
            # The new runtime is backward-compatible with the old boot disk;
            # installing it first also leaves a safe pair if A: replacement fails.
            if runtime is not None:
                os.replace(work / 'cpmsim', instance / 'runtime/cpmsim')
                os.replace(work / 'cpmsim.features.json', instance / 'runtime/cpmsim.features.json')
            os.replace(staged, image)
            os.replace(pending_manifest, manifest_file)
        print('Updated the stopped boot disk. Existing BBS users/messages and all data disks are preserved.')
        print('Rollback boot disk: ' + str(backup))
        if runtime is not None:
            print('Updated matching emulator; rollback runtime: ' + str(runtime_backup))
        print('Run Start-RCPM.command to restart on the existing port.')
        if enable_rbbs:
            print('Callers can now enter RBBS at the CP/M prompt; SYSUTLS remains private.')
        return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--builds', type=Path, default=Path('build/bye5'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--enable-rbbs', action='store_true', help='Install public RBBS entry and migrate the previous caller policy')
    parser.add_argument('--runtime', type=Path, help='Matching emulator for drivers requiring the idle timer')
    args = parser.parse_args()
    try:
        upgrade(*(getattr(args, name).expanduser().resolve() for name in ('instance', 'builds', 'cpmtools')),
                args.enable_rbbs, args.runtime.expanduser().resolve() if args.runtime else None)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
