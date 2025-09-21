import requests
import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# Initialize Earth Engine
ee.Authenticate();
ee.Initialize(project='sartech-api')

# ====== 1. Define common bounding box ======
# Using Princeton/Lawrence Township area in New Jersey (forests, D&R Canal, roads)
# Format: south,west,north,east for OSM
bbox_osm = "40.30,-74.70,40.38,-74.60"
# Format: [west, south, east, north] for Earth Engine  
bbox_ee = [-74.70, 40.30, -74.60, 40.38]
roi = ee.Geometry.Rectangle(bbox_ee)

print("Fetching data from multiple sources...")

# ====== 2. Get Roads from OpenStreetMap ======
print("Fetching roads from OpenStreetMap...")
overpass_url = "https://overpass-api.de/api/interpreter"
query = f"""
[out:json];
way["highway"]({bbox_osm});
(._;>;);
out geom;
"""

try:
    response = requests.get(overpass_url, params={"data": query})
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

# ====== 3. Get Water from Google Earth Engine ======
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

# ====== 4. Get Forests from Hansen Dataset ======
print("Fetching forest coverage from Hansen dataset...")
try:
    hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10').select('treecover2000')
    
    # Create two forest masks for different densities
    sparse_forest_mask = hansen.gte(10).And(hansen.lt(50)).selfMask()  # 10-50% tree cover
    dense_forest_mask = hansen.gte(50).selfMask()  # 50%+ tree cover
    
    sparse_forest_roi = sparse_forest_mask.clip(roi)
    dense_forest_roi = dense_forest_mask.clip(roi)
    
    # Convert sparse forests to vectors
    sparse_forest_polygons = sparse_forest_roi.reduceToVectors(
        geometry=roi,
        scale=30,
        geometryType='polygon',
        eightConnected=True,
        labelProperty='sparse_forest',
        maxPixels=1e10
    )
    
    # Convert dense forests to vectors
    dense_forest_polygons = dense_forest_roi.reduceToVectors(
        geometry=roi,
        scale=30,
        geometryType='polygon',
        eightConnected=True,
        labelProperty='dense_forest',
        maxPixels=1e10
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
    
    print(f"Found {len(sparse_forest_patches)} sparse forest polygons (10-50% cover)")
    print(f"Found {len(dense_forest_patches)} dense forest polygons (50%+ cover)")
    
except Exception as e:
    print(f"Error fetching forests: {e}")
    sparse_forest_patches = []
    dense_forest_patches = []

# ====== 5. Create Combined Visualization ======
print("Creating combined visualization...")
fig, ax = plt.subplots(figsize=(15, 12))

# Plot sparse forests first (background layer)
if sparse_forest_patches:
    sparse_forest_collection = PatchCollection(
        sparse_forest_patches, 
        facecolor='lightgreen', 
        edgecolor='none', 
        alpha=0.5,
        label='Sparse forests (10-50% cover)'
    )
    ax.add_collection(sparse_forest_collection)

# Plot dense forests (darker, on top of sparse)
if dense_forest_patches:
    dense_forest_collection = PatchCollection(
        dense_forest_patches, 
        facecolor='darkgreen', 
        edgecolor='none', 
        alpha=0.7,
        label='Dense forests (50%+ cover)'
    )
    ax.add_collection(dense_forest_collection)

# Plot water features
if water_patches:
    water_collection = PatchCollection(
        water_patches, 
        facecolor='blue', 
        edgecolor='darkblue', 
        alpha=0.7,
        label='Water bodies'
    )
    ax.add_collection(water_collection)

# Plot roads on top
if roads:
    for road in roads:
        lons, lats = zip(*road)
        ax.plot(lons, lats, color="gray", linewidth=2, alpha=0.8)

# Create a dummy line for roads legend
if roads:
    ax.plot([], [], color="gray", linewidth=2, alpha=0.8, label='Roads')

# Set plot boundaries
west, south, east, north = bbox_ee

# Formatting
ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)
ax.set_title('Combined Map: Forests, Water Bodies, and Roads\nPrinceton/Lawrence Township, NJ', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

# Force axis limits after all data is plotted
ax.set_xlim(west, east)
ax.set_ylim(south, north)
ax.legend(loc='upper right')

# Add feature counts as text
info_text = f"Features displayed:\n"
info_text += f"• Roads: {len(roads)} segments\n"
info_text += f"• Water: {len(water_patches)} polygons\n"
info_text += f"• Sparse forests: {len(sparse_forest_patches)} polygons\n"
info_text += f"• Dense forests: {len(dense_forest_patches)} polygons"

ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
        verticalalignment='top', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

plt.tight_layout()
plt.show()

print("Combined map visualization complete!")