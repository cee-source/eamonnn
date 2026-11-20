from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from tools import ble, wifi, lure

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

# ── BLE ──────────────────────────────────────────────
@app.route('/api/ble/scan')
def ble_scan():
    timeout = float(request.args.get('timeout', 5))
    result = ble.scan(timeout)
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify({'devices': result, 'count': len(result)})

# ── WiFi ─────────────────────────────────────────────
@app.route('/api/wifi/scan')
def wifi_scan():
    result = wifi.scan()
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500
    return jsonify({'networks': result, 'count': len(result)})

# ── Lure Trap ─────────────────────────────────────────
@app.route('/api/lure/status')
def lure_status():
    return jsonify(lure.status())

@app.route('/api/lure/start', methods=['POST'])
def lure_start():
    ssid = (request.json or {}).get('ssid', 'Free WiFi')
    return jsonify(lure.start(ssid))

@app.route('/api/lure/stop', methods=['POST'])
def lure_stop():
    return jsonify(lure.stop())

if __name__ == '__main__':
    print('\n  FlipKit Tools → http://localhost:5000\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
