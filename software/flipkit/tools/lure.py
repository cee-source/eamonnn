import subprocess, os, signal, tempfile, threading

_procs = {}

HOSTAPD_CONF = """\
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""

DNSMASQ_CONF = """\
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
address=/#/192.168.4.1
"""

def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def start(ssid='Free WiFi'):
    if _procs.get('hostapd'):
        return {'error': 'Already running'}

    # write configs to temp files
    hconf = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
    hconf.write(HOSTAPD_CONF.format(ssid=ssid))
    hconf.flush()

    dconf = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
    dconf.write(DNSMASQ_CONF)
    dconf.flush()

    # bring up wlan0 with static IP
    _run(['sudo', 'ip', 'addr', 'add', '192.168.4.1/24', 'dev', 'wlan0'])
    _run(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'])

    # start hostapd
    hp = subprocess.Popen(['sudo', 'hostapd', hconf.name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _procs['hostapd'] = hp
    _procs['hostapd_conf'] = hconf.name

    # start dnsmasq
    dp = subprocess.Popen(['sudo', 'dnsmasq', '--no-daemon', '-C', dconf.name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _procs['dnsmasq'] = dp
    _procs['dnsmasq_conf'] = dconf.name
    _procs['ssid'] = ssid

    return {'status': 'started', 'ssid': ssid, 'ip': '192.168.4.1'}

def stop():
    for key in ('hostapd', 'dnsmasq'):
        p = _procs.pop(key, None)
        if p:
            try:
                subprocess.run(['sudo', 'kill', str(p.pid)])
            except Exception:
                pass
    for key in ('hostapd_conf', 'dnsmasq_conf'):
        path = _procs.pop(key, None)
        if path and os.path.exists(path):
            os.unlink(path)
    _run(['sudo', 'ip', 'addr', 'del', '192.168.4.1/24', 'dev', 'wlan0'])
    _procs.pop('ssid', None)
    return {'status': 'stopped'}

def status():
    running = bool(_procs.get('hostapd'))
    return {
        'running': running,
        'ssid':    _procs.get('ssid', '—') if running else '—',
    }
