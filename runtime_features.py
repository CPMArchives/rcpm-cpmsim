"""Require a matching emulator before installing drivers with added I/O devices."""
import hashlib
import json


def require(runtime, build):
    if build.get('idle_timer_port') != 74:
        return
    path = runtime.with_name(runtime.name + '.features.json')
    if not path.is_file():
        raise ValueError('This BYE driver needs the matching port-74 timer runtime: ' + str(runtime))
    data = json.loads(path.read_text())
    if build.get('du_authorization') and not data.get('sysop_writable_catalog'):
        raise ValueError('AUTH-enabled BYE needs the sysop-writable catalog runtime')
    if data.get('idle_timer_port') != 74 or data.get('sha256') != hashlib.sha256(runtime.read_bytes()).hexdigest():
        raise ValueError('Emulator feature metadata does not match the selected BYE driver/runtime')
