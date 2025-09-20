import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# Initialize EE
ee.Initialize(project='sartech-api')

# --- ROI in forested area ---
roi = ee.Geometry.Rectangle([-74.4, 40.85, -74.1, 41.05])

# --- Load Proba-V landcover ---
landcover_col = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global")
landcover = landcover_col.first().select('discrete_classification')

# --- Mask forest (class 50) ---
forest_mask = landcover.eq(50).selfMask()
forest_roi = forest_mask.clip(roi)

# --- Vectorize ---
forest_polygons = forest_roi.reduceToVectors(
    geometry=roi,
    scale=100,
    geometryType='polygon',
    eightConnected=True,
    labelProperty='forest',
    maxPixels=1e10
)

# --- Convert to matplotlib patches ---
geojson = forest_polygons.getInfo()
patches = []
for feature in geojson['features']:
    geom = shape(feature['geometry'])
    if isinstance(geom, Polygon):
        patches.append(MplPolygon(list(geom.exterior.coords), closed=True))
    elif isinstance(geom, MultiPolygon):
        for poly in geom.geoms:
            patches.append(MplPolygon(list(poly.exterior.coords), closed=True))

# --- Plot ---
fig, ax = plt.subplots(figsize=(10,10))
ax.add_collection(PatchCollection(patches, facecolor='green', edgecolor='black', alpha=0.5))

coords = roi.getInfo()['coordinates'][0]
min_lon, min_lat = coords[0]
max_lon, max_lat = coords[2]
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Forest Polygons')
plt.show()
