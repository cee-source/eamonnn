import os, subprocess, glob

def check_camera():
    return any(os.path.exists(p) for p in ['/dev/video0', '/dev/video1'])

def check_spi(bus=0, dev=0):
    return os.path.exists(f'/dev/spidev{bus}.{dev}')

def check_lirc():
    return bool(glob.glob('/dev/lirc*'))

def check_tor():
    r = subprocess.run(['systemctl', 'is-active', 'tor'],
                       capture_output=True, text=True)
    return r.stdout.strip() == 'active'

def status_all():
    return {
        'camera':  check_camera(),
        'rfid':    check_spi(0, 0),
        'subghz':  check_spi(1, 0),
        'ir':      check_lirc(),
        'nfc':     check_spi(0, 1),
        'tor':     check_tor(),
    }
