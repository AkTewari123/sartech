from flask import Flask, jsonify
from mcs import OptimizedSwarmBot, NUM_BOTS

app = Flask(__name__)

@app.route("/simulate", methods=["GET"])
def simulate_swarm():
    """
    Run the optimized swarm simulation and return bot data as JSON,
    in the same format that would have been written to CSV.
    """
    try:
        # Initialize simulation (you can change image_path and location)
        simulation = OptimizedSwarmBot('image.png', lat_center=40.7128, lon_center=-74.0060)
        
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
        
        return jsonify({"num_bots": NUM_BOTS, "bots": bots_data})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Runs the Flask server continuously
    app.run(host="0.0.0.0", port=8080, debug=True)
