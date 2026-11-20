import subprocess, os, signal, tempfile, time, re

_state = {}

BARESIP_CFG = """\
{sip_listen        0.0.0.0:0}
{audio_player      default}
{audio_source      default}
{ausrc_srate       48000}
{auplay_srate      48000}
"""

ACCOUNT_LINE = "<sip:{user}@{server}>;auth_pass={password};outbound=\"sip:{server}\""

def _write_config(user, server, password):
    cfg_dir = os.path.expanduser('~/.config/flipkit_baresip')
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, 'config'), 'w') as f:
        f.write(BARESIP_CFG)
    with open(os.path.join(cfg_dir, 'accounts'), 'w') as f:
        f.write(ACCOUNT_LINE.format(user=user, server=server, password=password) + '\n')
    return cfg_dir

def start(user, server, password):
    if _state.get('proc'):
        return {'error': 'Already running'}
    cfg_dir = _write_config(user, server, password)
    # check tor is running
    tor = subprocess.run(['systemctl', 'is-active', 'tor'],
                         capture_output=True, text=True)
    if tor.stdout.strip() != 'active':
        subprocess.run(['sudo', 'systemctl', 'start', 'tor'])
        time.sleep(2)
    # start baresip via torsocks — routes all SIP + RTP through Tor
    proc = subprocess.Popen(
        ['torsocks', 'baresip', '-f', cfg_dir, '-e', '/quit'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    _state['proc'] = proc
    _state['user'] = user
    _state['server'] = server
    # collect startup output for a moment
    time.sleep(2)
    output = []
    while True:
        try:
            proc.stdout.read(1)  # non-blocking drain
            break
        except Exception:
            break
    return {'status': 'started', 'identity': f'sip:{user}@{server}', 'tor': True}

def dial(number, server):
    proc = _state.get('proc')
    if not proc:
        return {'error': 'Not connected — start first'}
    try:
        proc.stdin.write(f'/dial sip:{number}@{server}\n')
        proc.stdin.flush()
    except Exception:
        pass
    return {'status': 'dialling', 'number': number}

def hangup():
    proc = _state.get('proc')
    if proc:
        try:
            proc.stdin.write('/hangup\n')
            proc.stdin.flush()
        except Exception:
            proc.terminate()
    _state.pop('proc', None)
    return {'status': 'hung up'}

def stop():
    proc = _state.pop('proc', None)
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass
    subprocess.run(['sudo', 'systemctl', 'stop', 'tor'])
    _state.clear()
    return {'status': 'stopped'}

def status():
    return {
        'connected': bool(_state.get('proc')),
        'identity':  f"sip:{_state['user']}@{_state['server']}" if _state.get('user') else '—',
        'tor':       _state.get('proc') is not None,
    }
