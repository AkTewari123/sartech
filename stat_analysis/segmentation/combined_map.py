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
# Using coordinates around 40.055910624826595, -76.91354490317927
# Format: south,west,north,east for OSM
bbox_osm = "40.005910,-76.96354,40.105910,-76.86354"
# Format: [west, south, east, north] for Earth Engine  
bbox_ee = [-76.96354, 40.005910, -76.86354, 40.105910]
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

# ====== 5. Create Clean Map Image ======
print("Creating clean map image...")

# Get plot boundaries
west, south, east, north = bbox_ee

# Create figure with no margins, axes, or decorations
fig = plt.figure(figsize=(12, 12), frameon=False)
ax = fig.add_axes([0, 0, 1, 1])  # Full figure, no margins
ax.set_xlim(west, east)
ax.set_ylim(south, north)

# Remove all axes elements
ax.axis('off')
ax.set_xticks([])
ax.set_yticks([])

# Set white background
fig.patch.set_facecolor('white')
ax.patch.set_facecolor('white')

# Fill entire plot area with white to ensure no transparency
from matplotlib.patches import Rectangle
white_bg = Rectangle((west, south), east-west, north-south, 
                    facecolor='white', edgecolor='none', zorder=0)
ax.add_patch(white_bg)

# Plot sparse forests first (background layer)
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
        ax.plot(lons, lats, color="#333333", linewidth=1.0, alpha=0.9, solid_capstyle='round')

# Save the clean image with explicit white background
plt.savefig('clean_combined_map.png', format='png', dpi=200, bbox_inches='tight', pad_inches=0, 
           facecolor='white', edgecolor='white', transparent=False)

plt.show()

print("Clean map image saved as 'clean_combined_map.png'")
print(f"Features displayed: Roads: {len(roads)}, Water: {len(water_patches)}, Sparse forests: {len(sparse_forest_patches)}, Dense forests: {len(dense_forest_patches)}")