import base64
import io
import uuid
from flask import Flask, request, jsonify
from supabase import create_client, Client
from datetime import datetime
from flask_cors import CORS
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

model = genai.GenerativeModel('gemini-1.5-pro-latest')
generation_config = genai.types.GenerationConfig(max_output_tokens=1024)

# --- Gemini API Configuration ---
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(f"Error: {e}")
    exit()
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
    return jsonify({"status": "this is pennapps!!"})

@app.route("/init_session", methods=["POST"])
def init_session():
    data = request.json or {}

    location = data.get("location", ["NO DATA", "NO DATA"])
    name = data.get("name", "NO DATA")
    description = data.get("description", "NO DATA")

    # Generate numeric ID using timestamp in milliseconds
    new_id = data.get("id", 12345678)

    # Check if this numeric ID already exists (very unlikely)
    existing = supabase.table("Raspberry Pi Sessions").select("*").eq("id", new_id).execute()
    if existing.data and len(existing.data) > 0:
        new_id += 1  # simple collision handling

    new_row = {
        "id": new_id,
        "latitude": location[0],
        "longitude": location[1],
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "resolved": False
    }

    response = supabase.table("Raspberry Pi Sessions").insert(new_row).execute()

    if hasattr(response, "error"):
        return jsonify({"error": str(response.error)}), 500

    return jsonify(response.data[0]), 201
@app.route("/upload_image", methods=["POST"])
def upload_image():
    data = request.json or {}

    bucket = data.get("bucket")
    image_base64 = data.get("image_base64")
    name = data.get("filename")

    if bucket not in ["pi-image", "base_comparison"]:
        return jsonify({"error": "Invalid bucket name"}), 400

    if not image_base64 or not name:
        return jsonify({"error": "Missing image_base64 or filename"}), 400

    filename = f"{name}.jpg"
    content_type = "image/jpeg"

    try:
        # Remove base64 prefix if present
        if "," in image_base64:
            header, image_base64 = image_base64.split(",", 1)
            if "png" in header:
                filename = f"{name}.png"
                content_type = "image/png"

        # ✅ Direct bytes
        image_bytes = base64.b64decode(image_base64)

        # Upload directly as bytes
        res = supabase.storage.from_(bucket).upload(
            path=filename,
            file=image_bytes,                       # <- raw bytes are valid here
            file_options={"content-type": content_type}
        )

        if hasattr(res, "error") and res.error:
            return jsonify({"error": str(res.error)}), 500

        public_url = supabase.storage.from_(bucket).get_public_url(filename)

        return jsonify({
            "message": "Upload successful",
            "bucket": bucket,
            "filename": filename,
            "public_url": public_url
        }), 201

    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500
@app.route("/check_similarity", methods=["POST"])
def check_similarity():
    """
    Receives JSON with two base64 images and asks Gemini if they depict the same person.
    JSON format:
    {
        "image1": "<base64 string>",
        "image2": "<base64 string>"
    }
    """
    try:
        data = request.json
        if not data or "image1" not in data or "image2" not in data:
            return jsonify({"error": "Request must include 'image1' and 'image2' base64 fields."}), 400

        # Decode images
        try:
            img1 = Image.open(io.BytesIO(base64.b64decode(data["image1"].split(",")[-1])))
            img2 = Image.open(io.BytesIO(base64.b64decode(data["image2"].split(",")[-1])))
        except Exception as e:
            return jsonify({"error": f"Invalid image data: {e}"}), 400

        # Prepare Gemini prompt
        prompt_text = (
            "You are a facial recognition assistant. Determine if the two provided images "
            "contain the same person. Respond with a short answer: 'Yes' or 'No', and optionally a confidence level. "
            "Do not include explanations or extra commentary."
        )

        # Send images and prompt to Gemini
        prompt_parts = [
            prompt_text,
            img1,
            img2
        ]

        print("Sending images to Gemini API for similarity check...")
        response = model.generate_content(
            contents=prompt_parts,
            generation_config=generation_config
        )
        print("Received response from Gemini API.")

        return jsonify({
            "message": "Success",
            "result": response.text.strip()
        })

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500, debug=True)
