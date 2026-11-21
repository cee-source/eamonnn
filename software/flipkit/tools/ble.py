import asyncio, subprocess, re
from bleak import BleakScanner, BleakClient

_MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$')

COMPANIES = {
    0x004C: 'Apple',
    0x0006: 'Microsoft',
    0x00E0: 'Google',
    0x0075: 'Samsung',
    0x0022: 'Qualcomm',
    0x000F: 'Broadcom',
    0x0010: 'Broadcom',
    0x0059: 'Nordic Semi',
    0x0046: 'MediaTek',
}

APPLE_TYPES = {
    0x00: 'iPhone',        0x01: 'Find My',
    0x02: 'iPhone',        0x03: 'AirPrint',
    0x04: 'AirPods',       0x05: 'AirTag',
    0x06: 'HomePod',       0x07: 'AirPods',
    0x08: 'Beats',         0x09: 'Nearby Action',
    0x0A: 'HomePod Mini',  0x0B: 'AirPods Gen3',
    0x0C: 'iPhone',        0x0D: 'iPad',
    0x0E: 'Apple Watch',   0x0F: 'AirPods Max',
    0x10: 'MacBook Pro',   0x11: 'iPhone',
    0x12: 'iPhone',        0x13: 'iPad',
    0x14: 'iPhone',        0x1E: 'MacBook',
    0x20: 'iPhone',        0x27: 'AirPods',
}

DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"


def _fingerprint_type(adv, adv_name):
    mfr = adv.manufacturer_data or {}
    name = adv_name or ''
    nl = name.lower()

    if 0x004C in mfr:
        data = mfr[0x004C]
        return APPLE_TYPES.get(data[0], 'Apple Device') if data else 'Apple Device'
    if 0x0006 in mfr:
        return 'Windows PC'
    if 0x00E0 in mfr:
        return 'Chromebook'
    if 0x0075 in mfr:
        return 'Samsung Android'

    if any(x in nl for x in ['iphone', 'ipad', 'macbook', 'imac', 'apple']):
        return 'Apple Device'
    if any(x in nl for x in ['galaxy', 'samsung']):
        return 'Samsung Android'
    if any(x in nl for x in ['pixel', 'android']):
        return 'Android'
    if any(x in nl for x in ['desktop', 'laptop', 'pc', 'windows']):
        return 'Windows PC'
    if 'chromebook' in nl:
        return 'Chromebook'

    for cid, vendor in COMPANIES.items():
        if cid in mfr:
            return vendor + ' Device'
    return 'Unknown'


def _btctl_name(address):
    """Check BlueZ name cache via bluetoothctl info."""
    try:
        r = subprocess.run(
            ['bluetoothctl', 'info', address],
            capture_output=True, text=True, timeout=2
        )
        # Try Name first, then Alias
        for pattern in [r'^\s+Name:\s+(.+)$', r'^\s+Alias:\s+(.+)$']:
            m = re.search(pattern, r.stdout, re.MULTILINE)
            if m:
                n = m.group(1).strip()
                # Ignore if it's just the MAC address
                if n and not re.match(r'^[0-9A-Fa-f:]+$', n):
                    return n
    except Exception:
        pass
    return None


async def _gatt_name(ble_device, timeout=2.5):
    """Connect to device and read Device Name characteristic."""
    try:
        async def _read():
            async with BleakClient(ble_device) as client:
                data = await client.read_gatt_char(DEVICE_NAME_UUID)
                name = data.decode('utf-8', errors='replace').strip()
                return name or None
        return await asyncio.wait_for(_read(), timeout=timeout)
    except Exception:
        return None


async def _scan(timeout):
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    if not results:
        return []

    # 1. Check BlueZ cache for all devices (fast, synchronous)
    btctl_names = {
        addr: _btctl_name(addr)
        for addr in results
    }

    # 2. For devices with no cached name, try GATT in parallel
    need_gatt = [
        (addr, dev)
        for addr, (dev, _adv) in results.items()
        if not btctl_names.get(addr) and not (dev.name or '')
    ]
    gatt_results = await asyncio.gather(
        *[_gatt_name(dev) for _, dev in need_gatt],
        return_exceptions=True
    )
    gatt_map = {
        addr: (name if isinstance(name, str) else None)
        for (addr, _), name in zip(need_gatt, gatt_results)
    }

    out = []
    for address, (device, adv) in results.items():
        rssi = adv.rssi if adv.rssi is not None else -120
        adv_name = device.name or adv.local_name or ''
        device_type = _fingerprint_type(adv, adv_name)

        # Priority: BlueZ cache > GATT > advertisement name > device type
        # Skip adv_name if it's just the MAC address echoed back
        clean_adv = adv_name if adv_name and not _MAC_RE.match(adv_name) else None
        username = (
            btctl_names.get(address) or
            gatt_map.get(address) or
            clean_adv or
            device_type
        )

        out.append({
            'name':        adv_name or device_type,
            'address':     address,
            'rssi':        rssi,
            'signal':      max(0, min(100, 100 + rssi)),
            'device_type': device_type,
            'username':    username,
        })

    return sorted(out, key=lambda x: x['rssi'], reverse=True)


def scan(timeout=5.0):
    try:
        return asyncio.run(_scan(timeout))
    except Exception as e:
        return {'error': str(e)}
