"""
IoT Web Dashboard Server - Water Gallon Inventory System
Flask REST API + live web dashboard accessible over LAN/Wi-Fi

Access from any device on the same network:
  http://<raspberry-pi-ip>:5000
  or
  http://<your-pc-ip>:5000
"""

from flask import Flask, jsonify, render_template, request, abort
from database import InventoryDatabase
from datetime import datetime
import socket
import threading

app = Flask(__name__)

# Shared state injected by main.py (or standalone use)
_db_name: str = "inventory.db"   # database filename (thread-safe - just a string)
_thread_local = threading.local()  # per-thread DB connections (SQLite is not thread-safe)
_sensor_state: dict = {
    "pressure_psi": None,
    "distance_cm": None,
    "valve_open": False,
    "conveyor_running": False,
    "leak_detected": False,
    "arduino1_connected": False,
    "arduino1_port": None,
    "arduino2_connected": False,
    "arduino2_port": None,
    "workflow_state": "IDLE",
    "last_updated": None,
}
_state_lock = threading.Lock()


def init_server(db: InventoryDatabase):
    """Call this before starting the server to set the database filename."""
    global _db_name
    _db_name = db.db_name  # just copy the filename; each thread opens its own connection


def get_db() -> InventoryDatabase:
    """Return a per-thread InventoryDatabase instance (creates one if needed)."""
    if not hasattr(_thread_local, "db"):
        _thread_local.db = InventoryDatabase(_db_name)
    return _thread_local.db


def update_sensor_state(**kwargs):
    """Thread-safe update of live sensor readings (called from main.py)."""
    with _state_lock:
        _sensor_state.update(kwargs)
        _sensor_state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# HTML Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Inventory
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/inventory")
def api_inventory():
    """Return all gallons as JSON."""
    gallons = get_db().get_all_gallons()
    return jsonify(gallons)


@app.route("/api/inventory/<inventory_id>")
def api_gallon(inventory_id):
    """Return a single gallon."""
    g = get_db().get_gallon(inventory_id)
    if not g:
        abort(404, description="Gallon not found")
    return jsonify(g)


@app.route("/api/inventory/<inventory_id>/refill", methods=["POST"])
def api_refill(inventory_id):
    """Trigger a refill increment remotely."""
    ok, msg = get_db().increment_refills(inventory_id)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)


@app.route("/api/inventory/<inventory_id>/defect", methods=["POST"])
def api_defect(inventory_id):
    """Report a defect remotely."""
    ok, msg = get_db().add_defect(inventory_id)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Statistics
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    """Return aggregate inventory stats."""
    stats = get_db().get_statistics()
    return jsonify(stats)


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Activity Log
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/activity")
def api_activity():
    """Return activity log (last 50 events)."""
    logs = get_db().get_activity_log()[:50]
    return jsonify(logs)


@app.route("/api/activity/<inventory_id>")
def api_activity_for_gallon(inventory_id):
    logs = get_db().get_activity_log(inventory_id)
    return jsonify(logs)


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Live Sensor / Workflow State
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/sensor")
def api_sensor():
    """Return the latest Arduino/sensor readings."""
    with _state_lock:
        return jsonify(dict(_sensor_state))


@app.route("/api/sensor", methods=["POST"])
def api_sensor_post():
    """
    Accept sensor data posted by the Arduino controller (or any client).
    Body: JSON with any subset of sensor_state keys.
    """
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="Expected JSON body")
    allowed = {"pressure_psi", "distance_cm", "valve_open",
                "conveyor_running", "leak_detected", "workflow_state",
                "arduino1_connected", "arduino1_port", "arduino2_connected", "arduino2_port"}
    update_sensor_state(**{k: v for k, v in data.items() if k in allowed})
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_local_ip() -> str:
    """Return the LAN IP address of this machine."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def run_server(db: InventoryDatabase, host: str = "0.0.0.0", port: int = 5000):
    """
    Start the Flask server — designed to be called in a daemon thread.
    Suppress the Flask development banner for cleaner output.
    """
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    init_server(db)
    app.run(host=host, port=port, debug=False, use_reloader=False)


def start_server_thread(db: InventoryDatabase, port: int = 5000) -> threading.Thread:
    """Spin up the Flask server in a background daemon thread."""
    t = threading.Thread(target=run_server, args=(db,), kwargs={"port": port}, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    # Standalone mode — creates its own DB connection
    db = InventoryDatabase()
    ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  IoT Dashboard running at:")
    print(f"  http://{ip}:5000   (LAN)")
    print(f"  http://127.0.0.1:5000 (local)")
    print(f"{'='*50}\n")
    run_server(db)
