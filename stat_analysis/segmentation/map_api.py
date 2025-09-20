from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
import requests
import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import io
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend

# Initialize Earth Engine
ee.Initialize(project='sartech-api')

app = FastAPI(title="Combined Map API", description="Generate maps with forests, water, and roads")

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

def generate_combined_map(bbox: BoundingBox) -> bytes:
    """Generate a clean map image (no axes/legends) and return as PNG bytes"""
    
    # Validate bounding box
    bbox.validate_bounds()
    
    # Format coordinates for different APIs
    bbox_osm = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"
    bbox_ee = [bbox.west, bbox.south, bbox.east, bbox.north]
    roi = ee.Geometry.Rectangle(bbox_ee)
    
    print(f"Generating clean map image for bounding box: {bbox_osm}")
    
    # ====== 1. Get Roads from OpenStreetMap ======
    print("Fetching roads from OpenStreetMap...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    way["highway"]({bbox_osm});
    (._;>;);
    out geom;
    """
    
    try:
        response = requests.get(overpass_url, params={"data": query}, timeout=30)
        response.raise_for_status()
        osm_data = response.json()
        
        roads = []
        for element in osm_data["elements"]:
            if element["type"] == "way" and "geometry" in element:
                coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
                roads.append(coords)
        print(f"Found {len(roads)} road segments")
    except Exception as e:
        print(f"Error fetching roads: {e}")
        roads = []
    
    # ====== 2. Get Water from Google Earth Engine ======
    print("Fetching water features from Google Earth Engine...")
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
        water_patches = []
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
        water_patches = []
    
    # ====== 3. Get Forests from Hansen Dataset ======
    print("Fetching forest coverage from Hansen dataset...")
    try:
        hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10').select('treecover2000')
        
        # Create two forest masks for different densities
        sparse_forest_mask = hansen.gte(10).And(hansen.lt(50)).selfMask()  # 10-50% tree cover
        dense_forest_mask = hansen.gte(50).selfMask()  # 50%+ tree cover
        
        sparse_forest_roi = sparse_forest_mask.clip(roi)
        dense_forest_roi = dense_forest_mask.clip(roi)
        
        # Convert forests to vectors
        sparse_forest_polygons = sparse_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='sparse_forest', maxPixels=1e10
        )
        
        dense_forest_polygons = dense_forest_roi.reduceToVectors(
            geometry=roi, scale=30, geometryType='polygon',
            eightConnected=True, labelProperty='dense_forest', maxPixels=1e10
        )
        
        # Process sparse forest patches
        sparse_forest_geojson = sparse_forest_polygons.getInfo()
        sparse_forest_patches = []
        for feature in sparse_forest_geojson['features']:
            geom = shape(feature['geometry'])
            if isinstance(geom, Polygon):
                sparse_forest_patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    sparse_forest_patches.append(MplPolygon(list(poly.exterior.coords), closed=True))
        
        # Process dense forest patches
        dense_forest_geojson = dense_forest_polygons.getInfo()
        dense_forest_patches = []
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
        sparse_forest_patches = []
        dense_forest_patches = []
    
    # ====== 4. Create Clean Map Image ======
    print("Creating clean map image...")
    
    # Create figure with no margins, axes, or decorations
    fig = plt.figure(figsize=(10, 10), frameon=False)
    ax = fig.add_axes([0, 0, 1, 1])  # Full figure, no margins
    ax.set_xlim(bbox.west, bbox.east)
    ax.set_ylim(bbox.south, bbox.north)
    
    # Remove all axes elements
    ax.axis('off')
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Set white background (change to transparent if needed later)
    fig.patch.set_facecolor('white')
    ax.patch.set_facecolor('white')
    
    # Plot sparse forests (lightest layer)
    if sparse_forest_patches:
        sparse_forest_collection = PatchCollection(
            sparse_forest_patches, 
            facecolor='#90EE90',  # Light green
            edgecolor='none', 
            alpha=0.6
        )
        ax.add_collection(sparse_forest_collection)
    
    # Plot dense forests (darker green)
    if dense_forest_patches:
        dense_forest_collection = PatchCollection(
            dense_forest_patches, 
            facecolor='#006400',  # Dark green
            edgecolor='none', 
            alpha=0.8
        )
        ax.add_collection(dense_forest_collection)
    
    # Plot water features (blue)
    if water_patches:
        water_collection = PatchCollection(
            water_patches, 
            facecolor='#0066CC',  # Blue
            edgecolor='none', 
            alpha=0.7
        )
        ax.add_collection(water_collection)
    
    # Plot roads (thin lines, high contrast)
    if roads:
        for road in roads:
            lons, lats = zip(*road)
            ax.plot(lons, lats, color="#333333", linewidth=0.8, alpha=0.9, solid_capstyle='round')
    
    # Save to bytes
    img_buffer = io.BytesIO()
    plt.savefig(
        img_buffer, 
        format='png', 
        dpi=200,  # High resolution
        bbox_inches='tight',
        pad_inches=0,  # No padding
        facecolor='white'  # White background
    )
    img_buffer.seek(0)
    plt.close(fig)  # Important: close figure to free memory
    
    print(f"Clean map image generated: {len(img_buffer.getvalue())} bytes")
    return img_buffer.getvalue()

@app.get("/")
async def root():
    return {"message": "Clean Map Image API - Generates clean PNG images without axes or labels"}

@app.post("/generate-map")
async def generate_map_endpoint(bbox: BoundingBox):
    """Generate a clean map image for the given bounding box.
    
    Returns a PNG image with no axes, legends, or labels - just the map features.
    Features included: forests (light/dark green), water bodies (blue), roads (dark gray).
    """
    try:
        # Generate the map
        image_bytes = generate_combined_map(bbox)
        
        # Return as PNG image with proper headers for web map overlay
        # Return as PNG image
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=map.png"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error generating map: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate map: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Map API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)