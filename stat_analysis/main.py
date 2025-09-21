from flask import Flask, request, jsonify
from supabase import create_client, Client
from datetime import datetime
from flask_cors import CORS
import os
from dotenv import load_dotenv
load_dotenv()
# -----------------------------
# Supabase setup
# -----------------------------
SUPABASE_URL = os.getenv("PROJECT_URL")
SUPABASE_KEY = os.getenv("ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)
CORS(app)  # Allow all origins

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

@app.route("/init_session", methods=["POST"])
def init_session():
    data = request.json or {}

    location = data.get("location", ["NO DATA", "NO DATA"])
    name = data.get("name", "NO DATA")
    description = data.get("description", "NO DATA")

    # Generate numeric ID using timestamp in milliseconds
    new_id = int(datetime.utcnow().timestamp() * 1000)

    # Check if this numeric ID already exists (very unlikely)
    existing = supabase.table("Raspberry Pi Sessions").select("*").eq("id", new_id).execute()
    if existing.data and len(existing.data) > 0:
        new_id += 1  # simple collision handling

    new_row = {
        "id": new_id,
        "location": location,
        "name": name,
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "resolved": False
    }

    response = supabase.table("Raspberry Pi Sessions").insert(new_row).execute()

    if response.error:
        return jsonify({"error": str(response.error)}), 500

    return jsonify(response.data[0]), 201

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500, debug=True)
