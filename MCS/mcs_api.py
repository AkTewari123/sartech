from flask import Flask, jsonify, request
from flask_cors import CORS
from mcs import OptimizedSwarmBot, NUM_BOTS
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

@app.route("/simulate", methods=["GET", "POST"])
def simulate_swarm():
    """
    Run the optimized swarm simulation and return bot data as JSON,
    in the same format that would have been written to CSV.
    Supports both GET and POST requests with optional coordinates.
    """
    try:
        # Get coordinates from request
        if request.method == "POST":
            data = request.get_json()
            lat_center = data.get('lat_center', 40.7128)
            lon_center = data.get('lon_center', -74.0060)
        else:
            lat_center = float(request.args.get('lat_center', 40.7128))
            lon_center = float(request.args.get('lon_center', -74.0060))
        
        # Initialize simulation
        simulation = OptimizedSwarmBot('image.png', lat_center=lat_center, lon_center=lon_center)
        
        # Run simulation
        simulation.run_simulation()
        
        # Prepare CSV-like data
        bots_data = [
            {
                "x": float(simulation.bot_positions[i, 0]),
                "y": float(simulation.bot_positions[i, 1]),
                "age": float(simulation.bot_ages[i]),
                "speed": float(simulation.bot_speeds[i])
            }
            for i in range(NUM_BOTS)
        ]
        
        return jsonify({
            "num_bots": NUM_BOTS, 
            "bots": bots_data,
            "center_coords": {
                "lat": lat_center,
                "lng": lon_center
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate-heatmap", methods=["POST"])
def generate_heatmap():
    """
    Generate heatmap coordinates for flight planning from bounding box.
    This endpoint simulates potential search locations based on terrain analysis.
    """
    try:
        data = request.get_json()
        
        # Extract bounding box
        bbox = data.get('bbox', {})
        north = bbox.get('north')
        south = bbox.get('south') 
        east = bbox.get('east')
        west = bbox.get('west')
        
        if not all([north, south, east, west]):
            return jsonify({"error": "Missing bounding box coordinates"}), 400
        
        # Calculate center point for simulation
        lat_center = (north + south) / 2
        lon_center = (east + west) / 2
        
        # Run simulation to generate potential search locations
        simulation = OptimizedSwarmBot('image.png', lat_center=lat_center, lon_center=lon_center)
        simulation.run_simulation()
        
        # Convert bot positions to coordinates within the bounding box
        # Scale bot positions to fit within the actual geographic bounding box
        x_scale = (east - west) / 2000  # Assuming 2000x2000 simulation space
        y_scale = (north - south) / 2000
        
        heatmap_coords = []
        for i in range(NUM_BOTS):
            # Convert simulation coordinates to lat/lng
            lng = west + (simulation.bot_positions[i, 0] * x_scale)
            lat = south + (simulation.bot_positions[i, 1] * y_scale)
            
            heatmap_coords.append({
                "x": float(lng),  # longitude as x
                "y": float(lat),  # latitude as y
                "intensity": float(simulation.bot_ages[i]),  # use age as intensity
                "speed": float(simulation.bot_speeds[i])
            })
        
        return jsonify({
            "num_points": len(heatmap_coords),
            "coordinates": heatmap_coords,
            "bbox": bbox,
            "center": {
                "lat": lat_center,
                "lng": lon_center
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Runs the Flask server continuously
    app.run(host="0.0.0.0", port=8080, debug=True)
