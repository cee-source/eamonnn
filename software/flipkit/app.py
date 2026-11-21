from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
from tools import ble, wifi, lure, call, hw, bluenet, popup
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

PASSWORD = '7807809'

@app.before_request
def require_login():
    if request.endpoint not in ('login', 'static') and not session.get('auth'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['auth'] = True
            return redirect(url_for('index'))
        error = 'Wrong password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

# ── Hardware status ───────────────────────────────────
@app.route('/api/hw/status')
def hw_status():
    return jsonify(hw.status_all())

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

# ── Calling ───────────────────────────────────────────
@app.route('/api/call/status')
def call_status():
    return jsonify(call.status())

@app.route('/api/call/start', methods=['POST'])
def call_start():
    d = request.json or {}
    return jsonify(call.start(d.get('user',''), d.get('server',''), d.get('password','')))

@app.route('/api/call/dial', methods=['POST'])
def call_dial():
    d = request.json or {}
    return jsonify(call.dial(d.get('number',''), d.get('server','')))

@app.route('/api/call/hangup', methods=['POST'])
def call_hangup():
    return jsonify(call.hangup())

@app.route('/api/call/stop', methods=['POST'])
def call_stop():
    return jsonify(call.stop())

# ── BlueNet ───────────────────────────────────────────
@app.route('/api/bluenet/status')
def bluenet_status():
    return jsonify(bluenet.status())

@app.route('/api/bluenet/start', methods=['POST'])
def bluenet_start():
    d = request.json or {}
    return jsonify(bluenet.start(d.get('device_type', 'apple')))

@app.route('/api/bluenet/stop', methods=['POST'])
def bluenet_stop():
    return jsonify(bluenet.stop())

# ── Popups ────────────────────────────────────────
@app.route('/api/popup/status')
def popup_status():
    return jsonify(popup.status())

@app.route('/api/popup/start', methods=['POST'])
def popup_start():
    d = request.json or {}
    return jsonify(popup.start(d.get('popup_type', 'airpods')))

@app.route('/api/popup/stop', methods=['POST'])
def popup_stop():
    return jsonify(popup.stop())

if __name__ == '__main__':
    print('\n  FlipKit Tools → http://localhost:5000\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
