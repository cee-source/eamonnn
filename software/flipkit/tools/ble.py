import asyncio
from bleak import BleakScanner

# BLE company ID → vendor
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
    0x009E: 'Murata',
}

# Apple manufacturer data type byte → device type
APPLE_TYPES = {
    0x07: 'AirPods',
    0x09: 'AirPods Pro',
    0x0B: 'AirPods Gen3',
    0x0F: 'AirPods Max',
    0x05: 'AirTag',
    0x06: 'HomePod',
    0x0A: 'HomePod Mini',
    0x0C: 'iPhone/iPad',
    0x0D: 'iPad',
    0x0E: 'Apple Watch',
    0x1E: 'MacBook',
    0x08: 'Beats',
    0x03: 'AirPrint',
    0x01: 'Find My',
    0x10: 'MacBook Pro',
    0x14: 'iPhone',
}

# Windows Swift Pair company ID
MICROSOFT_ID = 0x0006

def _fingerprint(adv, device_name):
    """Return (device_type, username) from advertisement data."""
    mfr = adv.manufacturer_data or {}
    name = device_name or ''

    # Apple
    if 0x004C in mfr:
        data = mfr[0x004C]
        if data:
            apple_type = APPLE_TYPES.get(data[0], 'Apple Device')
            return apple_type, name or 'Apple User'

    # Microsoft / Windows
    if MICROSOFT_ID in mfr:
        return 'Windows PC', name or 'Windows User'

    # Google / Android / Chromebook
    if 0x00E0 in mfr:
        return 'Chromebook', name or 'Google User'

    # Samsung
    if 0x0075 in mfr:
        return 'Samsung Android', name or 'Samsung User'

    # Guess from name patterns
    nl = name.lower()
    if any(x in nl for x in ["iphone", "ipad", "macbook", "imac", "apple"]):
        return 'Apple Device', name
    if any(x in nl for x in ["galaxy", "samsung"]):
        return 'Samsung Android', name
    if any(x in nl for x in ["pixel", "android"]):
        return 'Android', name
    if any(x in nl for x in ["desktop", "laptop", "pc", "windows"]):
        return 'Windows PC', name
    if any(x in nl for x in ["chromebook"]):
        return 'Chromebook', name

    # Fallback: use first company match
    for cid, vendor in COMPANIES.items():
        if cid in mfr:
            return vendor + ' Device', name or 'Unknown'

    # Try to guess from service UUIDs
    if adv.service_uuids:
        for uuid in adv.service_uuids:
            if '1800' in uuid or '180a' in uuid.lower():
                return 'BLE Device', name or 'Unknown'

    return 'Unknown', name or 'Unknown'


async def _scan(timeout):
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    out = []
    for address, (device, adv) in results.items():
        rssi = adv.rssi if adv.rssi is not None else -120
        device_type, username = _fingerprint(adv, device.name)
        out.append({
            'name':        device.name or 'Unknown',
            'address':     device.address,
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
