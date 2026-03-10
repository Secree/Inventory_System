"""
Cloud Logger — Optional Firebase Realtime Database sync.

Usage:
  1. Create a Firebase project and download the service account key JSON.
  2. Save it as  firebase_credentials.json  in the project root.
  3. Set your database URL in  firebase_config.json  (see TEMPLATE below).

If credentials or config are missing the logger silently does nothing,
so the desktop app works fine even without a cloud connection.

FIREBASE_CONFIG TEMPLATE (firebase_config.json):
{
    "database_url": "https://your-project-default-rtdb.firebaseio.com"
}
"""

import json
import os
import threading
from datetime import datetime

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "firebase_credentials.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "firebase_config.json")

_firebase_db = None          # Firebase db reference (firebase_admin)
_firebase_ready = False
_log_lock = threading.Lock()


def _load_firebase():
    """Initialise Firebase Admin SDK (called once at import time)."""
    global _firebase_db, _firebase_ready

    if not os.path.isfile(CREDENTIALS_FILE):
        print("[CloudLogger] firebase_credentials.json not found — cloud sync disabled.")
        return
    if not os.path.isfile(CONFIG_FILE):
        print("[CloudLogger] firebase_config.json not found — cloud sync disabled.")
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, db as firebase_db_module

        with open(CONFIG_FILE) as f:
            cfg = json.load(f)

        database_url = cfg.get("database_url", "")
        if not database_url:
            print("[CloudLogger] 'database_url' missing in firebase_config.json.")
            return

        if not firebase_admin._apps:
            cred = credentials.Certificate(CREDENTIALS_FILE)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})

        _firebase_db = firebase_db_module
        _firebase_ready = True
        print(f"[CloudLogger] Connected to Firebase: {database_url}")

    except ImportError:
        print("[CloudLogger] firebase-admin not installed — run: pip install firebase-admin")
    except Exception as e:
        print(f"[CloudLogger] Initialisation error: {e}")


def _push(path: str, data: dict):
    """
    Push data to Firebase in a background thread so it never blocks the UI.
    """
    if not _firebase_ready:
        return

    def _worker():
        try:
            with _log_lock:
                ref = _firebase_db.reference(path)
                ref.push(data)
        except Exception as e:
            print(f"[CloudLogger] Push error ({path}): {e}")

    threading.Thread(target=_worker, daemon=True).start()


def _set(path: str, data: dict):
    """Overwrite a node in Firebase."""
    if not _firebase_ready:
        return

    def _worker():
        try:
            with _log_lock:
                ref = _firebase_db.reference(path)
                ref.set(data)
        except Exception as e:
            print(f"[CloudLogger] Set error ({path}): {e}")

    threading.Thread(target=_worker, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def log_gallon_added(inventory_id: str, name: str):
    _push("events/gallon_added", {
        "inventory_id": inventory_id,
        "name": name,
        "timestamp": datetime.now().isoformat(),
    })


def log_refill(inventory_id: str, name: str):
    _push("events/refills", {
        "inventory_id": inventory_id,
        "name": name,
        "timestamp": datetime.now().isoformat(),
    })


def log_defect(inventory_id: str, name: str):
    _push("events/defects", {
        "inventory_id": inventory_id,
        "name": name,
        "timestamp": datetime.now().isoformat(),
    })


def log_sensor_reading(pressure_psi, distance_cm, valve_open: bool,
                        leak_detected: bool, workflow_state: str):
    """Update the live sensor node (overwrites — it's the latest snapshot)."""
    _set("live/sensor", {
        "pressure_psi": pressure_psi,
        "distance_cm": distance_cm,
        "valve_open": valve_open,
        "leak_detected": leak_detected,
        "workflow_state": workflow_state,
        "timestamp": datetime.now().isoformat(),
    })


def sync_stats(stats: dict):
    """Push full stats snapshot. Call periodically (e.g. every minute)."""
    _set("live/stats", {**stats, "timestamp": datetime.now().isoformat()})


def is_connected() -> bool:
    return _firebase_ready


# Initialise on import
_load_firebase()
