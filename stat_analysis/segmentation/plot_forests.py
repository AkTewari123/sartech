import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# Initialize Earth Engine
ee.Initialize(project="sartech-api")

# --- 1. Define ROI: Jamanxim deforested area in Brazil ---
roi = ee.Geometry.Rectangle([-118.271, 34.021, -118.243, 34.051])

# --- 2. Load Hansen Global Forest Change dataset ---
# Band 'treecover2000' = % tree cover in 2000
hansen = ee.Image('UMD/hansen/global_forest_change_2022_v1_10').select('treecover2000')

# --- 3. Mask forested pixels (choose threshold for sparse vs dense forests) ---
forest_mask = hansen.gte(10).selfMask()  # >=10% tree cover
forest_roi = forest_mask.clip(roi)

# --- 4. Convert raster to vectors ---
forest_polygons = forest_roi.reduceToVectors(
    geometry=roi,
    scale=20,               # 30 m resolution
    geometryType='polygon',
    eightConnected=True,
    labelProperty='forest',
    maxPixels=1e10
)

# --- 5. Convert to matplotlib patches ---
geojson = forest_polygons.getInfo()
patches = []
for feature in geojson['features']:
    geom = shape(feature['geometry'])
    if isinstance(geom, Polygon):
        patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
    elif isinstance(geom, MultiPolygon):
        for poly in geom.geoms:
            patches.append(MplPolygon(list(poly.exterior.coords), closed=True))

# --- 6. Plot with matplotlib ---
fig, ax = plt.subplots(figsize=(12,12))
ax.add_collection(PatchCollection(patches, facecolor='green', edgecolor='black', alpha=0.6))

coords = roi.getInfo()['coordinates'][0]
min_lon, min_lat = coords[0]
max_lon, max_lat = coords[2]
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Forest Coverage in Jamanxim National Forest (Hansen 2022, treecover >= 10%)')

plt.show()
