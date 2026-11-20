import subprocess, re

def _parse(raw):
    networks, cur = [], {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith('BSS '):
            if cur.get('ssid') or cur.get('bssid'):
                networks.append(cur)
            cur = {'bssid': line.split()[1].rstrip('(on'), 'enc': 'Open'}
        elif re.match(r'SSID:', line):
            ssid = line[5:].strip()
            cur['ssid'] = ssid if ssid and ssid.strip('\x00') else '(null)'
        elif 'signal:' in line:
            try:
                dbm = float(line.split('signal:')[1].split()[0])
                cur['dbm']   = f'{dbm:.0f} dBm'
                cur['signal'] = max(0, min(100, int(100 + dbm)))
            except ValueError:
                pass
        elif 'freq:' in line:
            try:
                mhz = int(re.search(r'freq:\s*(\d+)', line).group(1))
                cur['band'] = '5GHz' if mhz > 4000 else '2.4GHz'
                cur['freq'] = f'{mhz} MHz'
            except (ValueError, AttributeError):
                pass
        elif 'RSN:' in line or 'WPA:' in line:
            cur['enc'] = 'WPA2' if 'RSN' in line else 'WPA'
    if cur.get('ssid') or cur.get('bssid'):
        networks.append(cur)
    return sorted(networks, key=lambda x: x.get('signal', 0), reverse=True)

def scan(iface='wlan0'):
    try:
        r = subprocess.run(
            ['sudo', 'iw', 'dev', iface, 'scan'],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode != 0:
            return {'error': r.stderr.strip() or 'Scan failed'}
        return _parse(r.stdout)
    except subprocess.TimeoutExpired:
        return {'error': 'Scan timed out'}
    except Exception as e:
        return {'error': str(e)}
