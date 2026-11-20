import asyncio
from bleak import BleakScanner, BleakClient

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
    0x07: 'AirPods',
    0x09: 'AirPods Pro',
    0x0B: 'AirPods Gen3',
    0x0F: 'AirPods Max',
    0x05: 'AirTag',
    0x06: 'HomePod',
    0x0A: 'HomePod Mini',
    0x0C: 'iPhone',
    0x0D: 'iPad',
    0x0E: 'Apple Watch',
    0x1E: 'MacBook',
    0x08: 'Beats',
    0x03: 'AirPrint',
    0x01: 'Find My',
    0x10: 'MacBook Pro',
    0x14: 'iPhone',
}

DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"


def _fingerprint_type(adv, adv_name):
    """Return device_type string from advertisement data."""
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


async def _gatt_name(address, timeout=2.0):
    """Connect to device and read the GATT Device Name characteristic."""
    try:
        client = BleakClient(address)
        await asyncio.wait_for(client.connect(), timeout=timeout)
        try:
            data = await asyncio.wait_for(
                client.read_gatt_char(DEVICE_NAME_UUID),
                timeout=1.5
            )
            name = data.decode('utf-8', errors='replace').strip()
            return name if name else None
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
    except Exception:
        return None


async def _scan(timeout):
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    if not results:
        return []

    # Try GATT name reads in parallel (2s timeout each — runs concurrently)
    addresses = list(results.keys())
    gatt_names = await asyncio.gather(
        *[_gatt_name(addr) for addr in addresses],
        return_exceptions=True
    )
    gatt_map = {
        addr: (name if isinstance(name, str) else None)
        for addr, name in zip(addresses, gatt_names)
    }

    out = []
    for address, (device, adv) in results.items():
        rssi = adv.rssi if adv.rssi is not None else -120
        adv_name = device.name or adv.local_name or ''
        device_type = _fingerprint_type(adv, adv_name)

        # Priority: GATT name > advertisement name > device type
        username = gatt_map.get(address) or adv_name or device_type

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
