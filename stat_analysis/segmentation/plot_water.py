import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# Initialize Earth Engine
ee.Initialize(project='sartech-api')

# --- 1. Define ROI ---
roi = ee.Geometry.Rectangle([-74.2, 40.7, -74.1, 40.75])

# --- 2. Load water dataset and mask ---
water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')
water_mask = water.gt(0).selfMask()
water_roi = water_mask.clip(roi)

# --- 3. Convert raster to vectors ---
water_polygons = water_roi.reduceToVectors(
    geometry=roi,
    scale=30,
    geometryType='polygon',
    eightConnected=True,
    labelProperty='water',
    maxPixels=1e10
)

# --- 4. Get polygon list as GeoJSON ---
geojson = water_polygons.getInfo()

# --- 5. Extract coordinates and convert to Shapely polygons ---
patches = []
for feature in geojson['features']:
    geom = feature['geometry']
    shapely_geom = shape(geom)  # Converts to Polygon or MultiPolygon

    if isinstance(shapely_geom, Polygon):
        patches.append(MplPolygon(list(shapely_geom.exterior.coords), closed=True))
    elif isinstance(shapely_geom, MultiPolygon):
        for poly in shapely_geom.geoms:
            patches.append(MplPolygon(list(poly.exterior.coords), closed=True))

# --- 6. Plot with matplotlib ---
fig, ax = plt.subplots(figsize=(8,8))
p = PatchCollection(patches, facecolor='blue', edgecolor='black', alpha=0.5)
ax.add_collection(p)

# Set plot limits to match ROI
coords = roi.getInfo()['coordinates'][0]
min_lon, min_lat = coords[0]
max_lon, max_lat = coords[2]
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Water Polygons')

plt.show()
