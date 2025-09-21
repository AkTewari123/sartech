from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load API key from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file.")

# Function to compare two images
def compare_images():
    try:
        # Ensure both images are provided in the request
        if "image1" not in request.files or "image2" not in request.files:
            return jsonify({"error": "Both image1 and image2 are required."}), 400

        # Get the images from the request
        image1 = request.files["image1"]
        image2 = request.files["image2"]

        # Prepare the request payload for the Gemini API
        url = "https://gemini.googleapis.com/v1/compareImages"
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
        }
        files = {
            "image1": (image1.filename, image1.stream, image1.content_type),
            "image2": (image2.filename, image2.stream, image2.content_type),
        }

        # Send the request to the Gemini API
        response = requests.post(url, headers=headers, files=files)

        # Check if the request was successful
        if response.status_code != 200:
            return jsonify({"error": "Failed to compare images.", "details": response.json()}), response.status_code

        # Return the comparison result
        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500
@app.route("/")
def health_check():
    return {
        "msg": "Deployment successful"
    }

@app.route("/post_image")
def post_image():
    pass
# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)