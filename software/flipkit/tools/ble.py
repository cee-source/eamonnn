import asyncio
from bleak import BleakScanner

async def _scan(timeout):
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    out = []
    for address, (device, adv) in results.items():
        rssi = adv.rssi if adv.rssi is not None else -120
        out.append({
            'name':    device.name or 'Unknown',
            'address': device.address,
            'rssi':    rssi,
            'signal':  max(0, min(100, 100 + rssi)),
        })
    return sorted(out, key=lambda x: x['rssi'], reverse=True)

def scan(timeout=5.0):
    try:
        return asyncio.run(_scan(timeout))
    except Exception as e:
        return {'error': str(e)}
