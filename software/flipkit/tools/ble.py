import asyncio
from bleak import BleakScanner

async def _scan(timeout):
    devices = await BleakScanner.discover(timeout=timeout)
    out = []
    for d in sorted(devices, key=lambda x: x.rssi or -120, reverse=True):
        out.append({
            'name':    d.name or 'Unknown',
            'address': d.address,
            'rssi':    d.rssi or -120,
            'signal':  max(0, min(100, 100 + (d.rssi or -120))),
        })
    return out

def scan(timeout=5.0):
    try:
        return asyncio.run(_scan(timeout))
    except Exception as e:
        return {'error': str(e)}
