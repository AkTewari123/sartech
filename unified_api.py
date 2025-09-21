from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import requests
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ee
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import sys
import os

from MCS.mcs import OptimizedSwarmBot, NUM_BOTS
from MCS.flightplan import (
    generate_density_map_from_data, 
    find_hotspots_with_dbscan, 
    plan_flight_path,
    select_distributed_pois,
    select_top_dense_grid_pois,
    plan_flight_path_in_order
)

ee.Initialize(project='sartech-api')

app = FastAPI(
    title="SARTech Unified API", 
    description="Comprehensive Search & Rescue Technology API",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELS ====================

class BoundingBox(BaseModel):
    south: float = Field(..., ge=-90, le=90, description="Southern latitude boundary")
    west: float = Field(..., ge=-180, le=180, description="Western longitude boundary") 
    north: float = Field(..., ge=-90, le=90, description="Northern latitude boundary")
    east: float = Field(..., ge=-180, le=180, description="Eastern longitude boundary")
    
    def validate_bounds(self):
        if self.south >= self.north:
            raise ValueError("South latitude must be less than north latitude")
        if self.west >= self.east:
            raise ValueError("West longitude must be less than east longitude")
        return self

class Coordinate(BaseModel):
    x: float
    y: float

class HotspotCluster(BaseModel):
    centroid: Coordinate
    points: List[Coordinate]
    size: int

class WorkflowRequest(BaseModel):
    bbox: BoundingBox
    eps: Optional[float] = 50.0
    min_samples: Optional[int] = 5
    generate_heatmap: Optional[bool] = True
    generate_flightplan: Optional[bool] = True

class WorkflowResponse(BaseModel):
    segmentation_layers: Optional[Dict[str, str]] = None
    heatmap_data: Optional[Dict[str, Any]] = None
    flight_plan_data: Optional[Dict[str, Any]] = None
    bbox: BoundingBox
    workflow_complete: bool = True

# ==================== SEGMENTATION FUNCTIONS ====================

def generate_feature_layers(bbox: BoundingBox) -> dict:
    """Generate separate layer images for each feature type"""
    
    bbox.validate_bounds()
    bbox_osm = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"
    bbox_ee = [bbox.west, bbox.south, bbox.east, bbox.north]
    roi = ee.Geometry.Rectangle(bbox_ee)
    
    print(f"Generating feature layers for bounding box: {bbox_osm}")
    
    # Get Roads from OpenStreetMap
    print("Fetching roads from OpenStreetMap...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    way["highway"]({bbox_osm});
    (._;>;);
    out geom;
    """
    
    roads = []
    try:
        response = requests.get(overpass_url, params={"data": query}, timeout=30)
        response.raise_for_status()
        osm_data = response.json()
        
        for element in osm_data["elements"]:
            if element["type"] == "way" and "geometry" in element:
                coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
                roads.append(coords)
        print(f"Found {len(roads)} road segments")
    except Exception as e:
        print(f"Error fetching roads: {e}")
    
    # Get Water from Google Earth Engine
    print("Fetching water features from Google Earth Engine...")
    water_patches = []
    try:
        water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')
        water_mask = water.gt(0).selfMask()
        water_roi = water_mask.clip(roi)
        
        water_polygons = water_roi.reduceToVectors(
            geometry=roi,
            scale=30,
            geometryType='polygon',
            eightConnected=True,
            labelProperty='water',
            maxPixels=1e10
        )
        
        water_geojson = water_polygons.getInfo()
        for feature in water_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                water_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    water_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        print(f"Found {len(water_patches)} water polygons")
    except Exception as e:
        print(f"Error fetching water: {e}")
    
    # Get Forests from Hansen Dataset
    print("Fetching forest coverage from Hansen dataset...")
    sparse_forest_patches = []
    dense_forest_patches = []
    try:
        hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10').select('treecover2000')
        
        sparse_forest_mask = hansen.gte(10).And(hansen.lt(50)).selfMask()
        dense_forest_mask = hansen.gte(50).selfMask()
        
        sparse_forest_roi = sparse_forest_mask.clip(roi)
        dense_forest_roi = dense_forest_mask.clip(roi)
        
        # Process sparse forest
        sparse_forest_polygons = sparse_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='sparse_forest', maxPixels=1e10
        )
        
        sparse_forest_geojson = sparse_forest_polygons.getInfo()
        for feature in sparse_forest_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                sparse_forest_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    sparse_forest_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        
        # Process dense forest
        dense_forest_polygons = dense_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='dense_forest', maxPixels=1e10
        )
        
        dense_forest_geojson = dense_forest_polygons.getInfo()
        for feature in dense_forest_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                dense_forest_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    dense_forest_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        
        print(f"Found {len(sparse_forest_patches)} sparse forest polygons")
        print(f"Found {len(dense_forest_patches)} dense forest polygons")
        
    except Exception as e:
        print(f"Error fetching forests: {e}")
    
    # Create Individual Layer Images
    layers = {}
    
    def create_layer_image(patches_dict, colors_dict, layer_name):
        """Create a single layer image with transparent background"""
        fig = plt.figure(figsize=(10, 10), frameon=False)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(bbox.west, bbox.east)
        ax.set_ylim(bbox.south, bbox.north)
        ax.axis('off')
        ax.set_xticks([])
        ax.set_yticks([])
        
        fig.patch.set_facecolor('white')
        fig.patch.set_alpha(0.0)
        ax.patch.set_facecolor('white')
        ax.patch.set_alpha(0.0)
        
        for patch_type, patches in patches_dict.items():
            if patches:
                if patch_type == 'roads':
                    for road in patches:
                        lons, lats = zip(*road)
                        ax.plot(lons, lats, color=colors_dict[patch_type], linewidth=2, alpha=0.9)
                else:
                    collection = PatchCollection(patches, facecolor=colors_dict[patch_type], 
                                               edgecolor='none', alpha=0.8)
                    ax.add_collection(collection)
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight',
                   pad_inches=0, facecolor='white', transparent=True)
        img_buffer.seek(0)
        plt.close(fig)
        
        img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        print(f"{layer_name} layer generated: {len(img_buffer.getvalue())} bytes")
        return img_data
    
    # Create layers
    if water_patches:
        layers['water'] = create_layer_image({'water': water_patches}, {'water': '#0066CC'}, 'Water')
    
    if sparse_forest_patches:
        layers['sparse_forest'] = create_layer_image(
            {'sparse_forest': sparse_forest_patches}, {'sparse_forest': '#90EE90'}, 'Sparse Forest')
    
    if dense_forest_patches:
        layers['dense_forest'] = create_layer_image(
            {'dense_forest': dense_forest_patches}, {'dense_forest': '#006400'}, 'Dense Forest')
    
    if roads:
        layers['roads'] = create_layer_image({'roads': roads}, {'roads': '#333333'}, 'Roads')
    
    return layers

# ==================== HEATMAP FUNCTIONS ====================

def create_combined_segmentation_image(bbox: BoundingBox, save_path: str = 'image.png') -> str:
    """Create a combined segmentation image for MCS simulation"""
    
    bbox.validate_bounds()
    bbox_osm = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"
    bbox_ee = [bbox.west, bbox.south, bbox.east, bbox.north]
    roi = ee.Geometry.Rectangle(bbox_ee)
    
    print(f"Creating combined segmentation image for bbox: {bbox_osm}")
    
    # Get all terrain features (reusing logic from generate_feature_layers)
    # Roads from OpenStreetMap
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    way["highway"]({bbox_osm});
    (._;>;);
    out geom;
    """
    
    roads = []
    try:
        response = requests.get(overpass_url, params={"data": query}, timeout=30)
        response.raise_for_status()
        osm_data = response.json()
        
        for element in osm_data["elements"]:
            if element["type"] == "way" and "geometry" in element:
                coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
                roads.append(coords)
        print(f"Found {len(roads)} road segments")
    except Exception as e:
        print(f"Error fetching roads: {e}")
    
    # Water from Google Earth Engine
    water_patches = []
    try:
        water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')
        water_mask = water.gt(0).selfMask()
        water_roi = water_mask.clip(roi)
        
        water_polygons = water_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='water', maxPixels=1e10
        )
        
        water_geojson = water_polygons.getInfo()
        for feature in water_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                water_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    water_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        print(f"Found {len(water_patches)} water polygons")
    except Exception as e:
        print(f"Error fetching water: {e}")
    
    # Forests from Hansen Dataset
    sparse_forest_patches = []
    dense_forest_patches = []
    try:
        hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10').select('treecover2000')
        
        sparse_forest_mask = hansen.gte(10).And(hansen.lt(50)).selfMask()
        dense_forest_mask = hansen.gte(50).selfMask()
        
        sparse_forest_roi = sparse_forest_mask.clip(roi)
        dense_forest_roi = dense_forest_mask.clip(roi)
        
        # Process sparse forest
        sparse_forest_polygons = sparse_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='sparse_forest', maxPixels=1e10
        )
        
        sparse_forest_geojson = sparse_forest_polygons.getInfo()
        for feature in sparse_forest_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                sparse_forest_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    sparse_forest_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        
        # Process dense forest
        dense_forest_polygons = dense_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='dense_forest', maxPixels=1e10
        )
        
        dense_forest_geojson = dense_forest_polygons.getInfo()
        for feature in dense_forest_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                dense_forest_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    dense_forest_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        
        print(f"Found {len(sparse_forest_patches)} sparse forest polygons")
        print(f"Found {len(dense_forest_patches)} dense forest polygons")
        
    except Exception as e:
        print(f"Error fetching forests: {e}")
    
    # Create combined image with all terrain types
    fig = plt.figure(figsize=(10, 10), frameon=False)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(bbox.west, bbox.east)
    ax.set_ylim(bbox.south, bbox.north)
    ax.axis('off')
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Set white background
    fig.patch.set_facecolor('white')
    ax.patch.set_facecolor('white')
    
    # Add terrain features in order (background to foreground)
    
    # 1. Water (blue)
    if water_patches:
        water_collection = PatchCollection(water_patches, facecolor='#0066CC', 
                                         edgecolor='none', alpha=1.0)
        ax.add_collection(water_collection)
    
    # 2. Sparse forests (light green)
    if sparse_forest_patches:
        sparse_collection = PatchCollection(sparse_forest_patches, facecolor='#90EE90', 
                                          edgecolor='none', alpha=1.0)
        ax.add_collection(sparse_collection)
    
    # 3. Dense forests (dark green)
    if dense_forest_patches:
        dense_collection = PatchCollection(dense_forest_patches, facecolor='#006400', 
                                         edgecolor='none', alpha=1.0)
        ax.add_collection(dense_collection)
    
    # 4. Roads (dark gray) - on top
    if roads:
        for road in roads:
            lons, lats = zip(*road)
            ax.plot(lons, lats, color='#333333', linewidth=2, alpha=1.0)
    
    # Save the combined image
    plt.savefig(save_path, format='png', dpi=200, bbox_inches='tight',
               pad_inches=0, facecolor='white')
    plt.close(fig)
    
    print(f"Combined segmentation image saved to: {save_path}")
    return save_path

def generate_heatmap_from_bbox(bbox: BoundingBox) -> dict:
    """Generate heatmap coordinates from bounding box using MCS simulation"""
    
    try:
        # First create the combined segmentation image that MCS needs
        image_path = create_combined_segmentation_image(bbox)
        
        # Calculate center point for simulation
        lat_center = (bbox.north + bbox.south) / 2
        lon_center = (bbox.east + bbox.west) / 2
        
        # Run simulation to generate potential search locations
        simulation = OptimizedSwarmBot(image_path, lat_center=lat_center, lon_center=lon_center)
        simulation.run_simulation()
        
        # FIXED: Proper coordinate conversion from simulation space to geographic coordinates
        # The simulation uses a 2000x2000 pixel space, we need to map this to the actual bounding box
        
        heatmap_coords = []
        for i in range(NUM_BOTS):
            # Convert from simulation pixel coordinates (0-2000) to normalized coordinates (0-1)
            normalized_x = simulation.bot_positions[i, 0] / 2000.0
            normalized_y = simulation.bot_positions[i, 1] / 2000.0
            
            # Map normalized coordinates to the actual bounding box
            # X maps to longitude (west to east)
            lng = bbox.west + normalized_x * (bbox.east - bbox.west)
            # Y maps to latitude (north to south) - NOTE: Y=0 is top in simulation, so we need to flip
            lat = bbox.north - normalized_y * (bbox.north - bbox.south)
            
            heatmap_coords.append({
                "x": float(lng),
                "y": float(lat),
                "intensity": float(simulation.bot_ages[i]),
                "speed": float(simulation.bot_speeds[i])
            })
        
        return {
            "num_points": len(heatmap_coords),
            "coordinates": heatmap_coords,
            "bbox": bbox.dict(),
            "center": {"lat": lat_center, "lng": lon_center}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating heatmap: {str(e)}")

# ==================== FLIGHT PLAN FUNCTIONS ====================

def generate_flight_plan_from_coords(coordinates: List[dict], eps: float = 10, min_samples: int = 3, min_waypoints: int = 6) -> dict:
    """Generate a simple flight plan:
    - Split space into 5x5 grid
    - Pick top 10 densest cells
    - Visit their centers in descending density order
    """
    
    try:
        # Convert to numpy array
        coords = np.array([[coord["x"], coord["y"]] for coord in coordinates])
        
        if len(coords) == 0:
            raise HTTPException(status_code=400, detail="No coordinates provided")
        
        # Grid-based densest cell selection (5x5, top 10)
        centers, cells_info, _, _ = select_top_dense_grid_pois(coords, grid_rows=5, grid_cols=5, top_k=10)

        # Start at mean of all coordinates
        start_point = (float(np.mean(coords[:, 0])), float(np.mean(coords[:, 1])))
        flight_path_array = plan_flight_path_in_order(centers, start_point=start_point)
        flight_path = [{"x": float(point[0]), "y": float(point[1])} for point in flight_path_array]

        # Format hotspots-like info from cells
        hotspots_data = [
            {"centroid": {"x": float(centers[i][0]), "y": float(centers[i][1])},
             "points": [],
             "size": int(cells_info[i]["count"]) if i < len(cells_info) else 0}
            for i in range(len(centers))
        ]

        return {
            "flight_path": flight_path,
            "hotspots": hotspots_data,
            "num_hotspots": len(hotspots_data),
            "num_waypoints": len(flight_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flight plan: {str(e)}")

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "message": "SARTech Unified API",
        "description": "Comprehensive Search & Rescue Technology Platform",
        "version": "1.0.0",
        "endpoints": {
            "/workflow": "POST - Complete analysis workflow",
            "/segmentation": "POST - Terrain segmentation only", 
            "/heatmap": "POST - Heatmap generation only",
            "/flightplan": "POST - Flight planning only",
            "/health": "GET - Health check"
        }
    }

@app.post("/workflow")
async def complete_workflow(request: WorkflowRequest):
    """
    Complete Search & Rescue analysis workflow:
    1. Generate terrain segmentation layers
    2. Create probability heatmap 
    3. Plan optimal flight path
    """
    try:
        print(f"Starting complete workflow for bbox: {request.bbox}")
        
        response = WorkflowResponse(bbox=request.bbox)
        
        # Step 1: Generate segmentation layers
        print("Step 1: Generating terrain segmentation...")
        segmentation_layers = generate_feature_layers(request.bbox)
        response.segmentation_layers = segmentation_layers
        
        # Step 2: Generate heatmap (if requested)
        if request.generate_heatmap:
            print("Step 2: Generating probability heatmap...")
            heatmap_data = generate_heatmap_from_bbox(request.bbox)
            response.heatmap_data = heatmap_data
            
            # Step 3: Generate flight plan (if requested)
            if request.generate_flightplan and heatmap_data.get("coordinates"):
                print("Step 3: Generating flight plan...")
                flight_plan_data = generate_flight_plan_from_coords(
                    heatmap_data["coordinates"], 
                    request.eps, 
                    request.min_samples,
                    6  # Ensure at least 6 waypoints
                )
                response.flight_plan_data = flight_plan_data
        
        print("Workflow completed successfully!")
        return response
        
    except Exception as e:
        print(f"Workflow error: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

@app.post("/segmentation")
async def segmentation_only(bbox: BoundingBox):
    """Generate terrain segmentation layers only"""
    try:
        layers = generate_feature_layers(bbox)
        return {
            "layers": layers,
            "bbox": bbox.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.post("/heatmap")
async def heatmap_only(bbox: BoundingBox):
    """Generate probability heatmap only"""
    try:
        heatmap_data = generate_heatmap_from_bbox(bbox)
        return heatmap_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {str(e)}")

@app.post("/flightplan")
async def flightplan_only(
    coordinates: List[Coordinate],
    eps: float = 50.0,
    min_samples: int = 3,
    min_waypoints: int = 6
):
    """Generate flight plan from coordinates only with guaranteed minimum waypoints"""
    try:
        coord_dicts = [{"x": coord.x, "y": coord.y} for coord in coordinates]
        flight_plan_data = generate_flight_plan_from_coords(coord_dicts, eps, min_samples, min_waypoints)
        return flight_plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flight planning failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "SARTech Unified API is running",
        "services": {
            "segmentation": "available",
            "heatmap": "available" if 'OptimizedSwarmBot' in globals() else "limited",
            "flightplan": "available" if 'find_hotspots_with_dbscan' in globals() else "limited"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting SARTech Unified API...")
    print("Available at: http://localhost:8000")
    print("Documentation at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)