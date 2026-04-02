import os
import gzip
import json
import threading
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file, render_template_string
from xml.etree import ElementTree as ET
import io
import re

app = Flask(__name__)

# --- Config ---
EPG_SOURCE_URL = "https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz"
OFFSETS_FILE = "offsets.json"
CACHE_FILE = "epg_cache.xml"
UPDATE_INTERVAL_HOURS = 6
DEFAULT_OFFSET_MINUTES = 1  # +1 minuto global por defeito

# --- State ---
last_update = None
update_lock = threading.Lock()

# --- Offsets ---
def load_offsets():
    if os.path.exists(OFFSETS_FILE):
        with open(OFFSETS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_offsets(offsets):
    with open(OFFSETS_FILE, "w") as f:
        json.dump(offsets, f, indent=2)

# --- EPG Processing ---
def parse_xmltv_time(t):
    # Format: 20240101120000 +0100
    t = t.strip()
    m = re.match(r"(\d{14})\s*([+-]\d{4})", t)
    if m:
        dt_str, tz_str = m.group(1), m.group(2)
        dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
        tz_sign = 1 if tz_str[0] == "+" else -1
        tz_hours = int(tz_str[1:3])
        tz_mins = int(tz_str[3:5])
        offset = timedelta(hours=tz_hours * tz_sign, minutes=tz_mins * tz_sign)
        return dt - offset, tz_str  # return UTC time + original tz string
    return None, None

def format_xmltv_time(dt, tz_str):
    return dt.strftime("%Y%m%d%H%M%S") + " " + tz_str

def apply_offset_to_time(t_str, offset_minutes):
    dt, tz_str = parse_xmltv_time(t_str)
    if dt is None:
        return t_str
    dt_new = dt + timedelta(minutes=offset_minutes)
    return format_xmltv_time(dt_new, tz_str)

def fetch_and_process_epg():
    global last_update
    with update_lock:
        print(f"[{datetime.now()}] A descarregar EPG...")
        try:
            resp = requests.get(EPG_SOURCE_URL, timeout=60)
            resp.raise_for_status()
            xml_data = gzip.decompress(resp.content)
        except Exception as e:
            print(f"Erro ao descarregar EPG: {e}")
            return False

        print("A processar EPG...")
        offsets = load_offsets()

        try:
            tree = ET.parse(io.BytesIO(xml_data))
            root = tree.getroot()
        except Exception as e:
            print(f"Erro ao parsear XML: {e}")
            return False

        for programme in root.findall("programme"):
            channel_id = programme.get("channel", "")
            offset = offsets.get(channel_id, DEFAULT_OFFSET_MINUTES)

            start = programme.get("start")
            stop = programme.get("stop")

            if start:
                programme.set("start", apply_offset_to_time(start, offset))
            if stop:
                programme.set("stop", apply_offset_to_time(stop, offset))

        # Save processed XML
        tree.write(CACHE_FILE, encoding="utf-8", xml_declaration=True)
        last_update = datetime.now()
        print(f"EPG atualizado com sucesso às {last_update}")
        return True

def get_all_channels():
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        tree = ET.parse(CACHE_FILE)
        root = tree.getroot()
        channels = []
        for ch in root.findall("channel"):
            cid = ch.get("id", "")
            name_el = ch.find("display-name")
            name = name_el.text if name_el is not None else cid
            channels.append({"id": cid, "name": name})
        return sorted(channels, key=lambda x: x["name"].lower())
    except:
        return []

# --- Background updater ---
def background_updater():
    while True:
        fetch_and_process_epg()
        time.sleep(UPDATE_INTERVAL_HOURS * 3600)

# --- Routes ---
@app.route("/epg.xml")
def serve_epg():
    if not os.path.exists(CACHE_FILE):
        fetch_and_process_epg()
    if not os.path.exists(CACHE_FILE):
        return "EPG ainda não disponível", 503
    return send_file(CACHE_FILE, mimetype="text/xml")

@app.route("/api/channels")
def api_channels():
    offsets = load_offsets()
    channels = get_all_channels()
    for ch in channels:
        ch["offset"] = offsets.get(ch["id"], DEFAULT_OFFSET_MINUTES)
    return jsonify(channels)

@app.route("/api/offset", methods=["POST"])
def api_set_offset():
    data = request.json
    channel_id = data.get("channel_id")
    offset = data.get("offset")
    if channel_id is None or offset is None:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    offsets = load_offsets()
    offsets[channel_id] = int(offset)
    save_offsets(offsets)
    return jsonify({"ok": True})

@app.route("/api/offset/bulk", methods=["POST"])
def api_set_bulk_offset():
    """Apply same offset to all channels"""
    data = request.json
    offset = data.get("offset")
    if offset is None:
        return jsonify({"error": "Offset inválido"}), 400
    channels = get_all_channels()
    offsets = load_offsets()
    for ch in channels:
        offsets[ch["id"]] = int(offset)
    save_offsets(offsets)
    return jsonify({"ok": True, "applied_to": len(channels)})

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=fetch_and_process_epg).start()
    return jsonify({"ok": True, "message": "Atualização iniciada"})

@app.route("/api/status")
def api_status():
    return jsonify({
        "last_update": last_update.isoformat() if last_update else None,
        "cache_exists": os.path.exists(CACHE_FILE),
        "source_url": EPG_SOURCE_URL,
        "default_offset": DEFAULT_OFFSET_MINUTES,
        "update_interval_hours": UPDATE_INTERVAL_HOURS
    })

@app.route("/")
def index():
    return render_template_string(open("index.html").read())

if __name__ == "__main__":
    # Start background updater
    t = threading.Thread(target=background_updater, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
