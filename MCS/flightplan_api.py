from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional
import numpy as np
import requests
from flightplan import (
    generate_density_map_from_data, 
    find_hotspots_with_dbscan, 
    plan_flight_path, 
    load_coords_from_csv
)
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

app = FastAPI(title="Flight Plan API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Coordinate(BaseModel):
    x: float
    y: float

class FlightPlanRequest(BaseModel):
    coordinates: List[Coordinate]
    eps: Optional[float] = 50.0
    min_samples: Optional[int] = 5
    map_size: Optional[Tuple[int, int]] = (2000, 2000)
    start_point: Optional[Tuple[float, float]] = None

class HotspotCluster(BaseModel):
    centroid: Coordinate
    points: List[Coordinate]
    size: int

class FlightPlanResponse(BaseModel):
    flight_path: List[Coordinate]
    hotspots: List[HotspotCluster]
    num_hotspots: int
    probability_map_base64: Optional[str] = None
    visualization_base64: Optional[str] = None

@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Flight Plan API",
        "description": "Generate optimized flight paths based on coordinate data using DBSCAN clustering",
        "endpoints": {
            "/generate-flight-plan": "POST - Generate flight plan from coordinates",
            "/analyze-from-csv": "GET - Analyze coordinates from CSV file"
        }
    }

@app.post("/generate-flight-plan", response_model=FlightPlanResponse)
def generate_flight_plan(request: FlightPlanRequest):
    """
    Generate an optimized flight plan from a set of coordinates.
    
    Args:
        request: FlightPlanRequest containing coordinates and parameters
        
    Returns:
        FlightPlanResponse with flight path, hotspots, and visualizations
    """
    try:
        # Convert input coordinates to numpy array
        coords = np.array([[coord.x, coord.y] for coord in request.coordinates])
        
        if len(coords) == 0:
            raise HTTPException(status_code=400, detail="No coordinates provided")
        
        # Find hotspots using DBSCAN
        hotspot_clusters = find_hotspots_with_dbscan(
            coords, 
            eps=request.eps, 
            min_samples=request.min_samples
        )
        
        if not hotspot_clusters:
            raise HTTPException(status_code=404, detail="No hotspots found. Try adjusting eps or min_samples parameters.")
        
        # Calculate centroids and prepare hotspot data
        hotspot_centroids = []
        hotspots_data = []
        
        for cluster in hotspot_clusters:
            centroid = np.mean(cluster, axis=0)
            hotspot_centroids.append(centroid)
            
            hotspots_data.append(HotspotCluster(
                centroid=Coordinate(x=float(centroid[0]), y=float(centroid[1])),
                points=[Coordinate(x=float(point[0]), y=float(point[1])) for point in cluster],
                size=len(cluster)
            ))
        
        # Generate flight path
        hotspot_centroids_array = np.array(hotspot_centroids)
        start_point = request.start_point or (
            np.random.uniform(0, request.map_size[0]), 
            np.random.uniform(0, request.map_size[1])
        )
        
        flight_path_array = plan_flight_path(hotspot_centroids_array, start_point=start_point)
        flight_path = [Coordinate(x=float(point[0]), y=float(point[1])) for point in flight_path_array]
        
        # Generate probability density map
        prob_map = generate_density_map_from_data(coords, map_size=request.map_size)
        
        # Generate base64 encoded probability map
        prob_map_b64 = generate_probability_map_image(prob_map)
        
        # Generate base64 encoded visualization
        visualization_b64 = generate_visualization_image(
            prob_map, hotspot_clusters, flight_path_array, coords
        )
        
        return FlightPlanResponse(
            flight_path=flight_path,
            hotspots=hotspots_data,
            num_hotspots=len(hotspots_data),
            probability_map_base64=prob_map_b64,
            visualization_base64=visualization_b64
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flight plan: {str(e)}")

@app.get("/analyze-from-csv")
def analyze_from_csv(
    filepath: str = "bots_600.csv",
    eps: float = 50.0,
    min_samples: int = 5,
    map_size_width: int = 2000,
    map_size_height: int = 2000
):
    """
    Analyze coordinates from a CSV file and generate flight plan.
    
    Args:
        filepath: Path to CSV file containing x,y coordinates
        eps: DBSCAN epsilon parameter
        min_samples: DBSCAN minimum samples parameter
        map_size_width: Width of the probability map
        map_size_height: Height of the probability map
        
    Returns:
        JSON response with flight plan data
    """
    try:
        # Load coordinates from CSV
        coords = load_coords_from_csv(filepath)
        
        if len(coords) == 0:
            raise HTTPException(status_code=400, detail=f"No valid coordinates found in {filepath}")
        
        # Create request object
        coordinate_list = [Coordinate(x=float(coord[0]), y=float(coord[1])) for coord in coords]
        request = FlightPlanRequest(
            coordinates=coordinate_list,
            eps=eps,
            min_samples=min_samples,
            map_size=(map_size_width, map_size_height)
        )
        
        # Generate flight plan
        return generate_flight_plan(request)
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CSV file {filepath} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing CSV file: {str(e)}")

def generate_probability_map_image(prob_map: np.ndarray) -> str:
    """Generate base64 encoded probability map image."""
    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(prob_map, cmap='hot', origin='upper')
    plt.colorbar(im, label='Probability')
    ax.set_title("Probability Density Map")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

def generate_visualization_image(prob_map: np.ndarray, hotspot_clusters: list, 
                                flight_path: np.ndarray, all_coords: np.ndarray) -> str:
    """Generate base64 encoded flight plan visualization."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot probability map
    im = ax.imshow(prob_map, cmap='hot', origin='upper')
    plt.colorbar(im, label='Probability')
    ax.set_title("Flight Plan Over Probability Map")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")

    # Plot original data points
    ax.scatter(all_coords[:, 0], all_coords[:, 1], color='gray', s=10, alpha=0.5, label='All Data Points')

    # Plot hotspot centroids
    for cluster in hotspot_clusters:
        centroid = np.mean(cluster, axis=0)
        ax.scatter(centroid[0], centroid[1], color='blue', marker='o', s=100, 
                  edgecolors='white', linewidths=1.5)

    # Plot flight path
    if len(flight_path) > 0:
        ax.plot(flight_path[:, 0], flight_path[:, 1], color='lime', linestyle='--', 
               linewidth=2, marker='^', markersize=8, label='Flight Path')
        ax.scatter(flight_path[0, 0], flight_path[0, 1], color='green', marker='s', 
                  s=150, label='Start Point', zorder=10)
    
    ax.legend()
    ax.grid(True, which='both', linestyle=':', linewidth=0.5)
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

@app.post("/generate-from-bbox")
async def generate_from_bbox(
    bbox: dict,
    mcs_api_url: str = "http://localhost:8080",
    eps: float = 50.0,
    min_samples: int = 5
):
    """
    Generate flight plan from bounding box by first getting heatmap data from MCS API.
    
    Args:
        bbox: Bounding box with north, south, east, west coordinates
        mcs_api_url: URL of the MCS API for heatmap generation
        eps: DBSCAN epsilon parameter
        min_samples: DBSCAN minimum samples parameter
        
    Returns:
        Combined response with heatmap data and flight plan
    """
    try:
        # Step 1: Get heatmap coordinates from MCS API
        mcs_response = requests.post(
            f"{mcs_api_url}/generate-heatmap",
            json={"bbox": bbox},
            timeout=30
        )
        
        if mcs_response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get heatmap data: {mcs_response.text}"
            )
        
        heatmap_data = mcs_response.json()
        coordinates = heatmap_data.get("coordinates", [])
        
        if not coordinates:
            raise HTTPException(status_code=400, detail="No heatmap coordinates generated")
        
        # Step 2: Convert to flight plan format
        coordinate_objects = [
            Coordinate(x=coord["x"], y=coord["y"]) 
            for coord in coordinates
        ]
        
        # Step 3: Generate flight plan
        flight_plan_request = FlightPlanRequest(
            coordinates=coordinate_objects,
            eps=eps,
            min_samples=min_samples,
            map_size=(2000, 2000)  # Use consistent map size
        )
        
        flight_plan_response = await generate_flight_plan(flight_plan_request)
        
        # Step 4: Combine responses
        return {
            "heatmap": heatmap_data,
            "flight_plan": flight_plan_response.dict(),
            "bbox": bbox,
            "workflow_complete": True
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to MCS API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flight plan from bbox: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)