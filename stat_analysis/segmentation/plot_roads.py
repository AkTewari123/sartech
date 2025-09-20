import ee
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, MultiPolygon
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

ee.Initialize(project='sartech-api')

# Define ROI
roi = ee.Geometry.Rectangle([-74.2, 40.7, -74.1, 40.75])

# Load roads dataset
roads = ee.FeatureCollection("TIGER/2016/Roads")
roads_roi = roads.filterBounds(roi)

geojson = roads_roi.getInfo()
patches = []
for feature in geojson['features']:
    shapely_geom = shape(feature['geometry'])
    if isinstance(shapely_geom, Polygon):
        patches.append(MplPolygon(list(shapely_geom.exterior.coords), closed=True))
    elif isinstance(shapely_geom, MultiPolygon):
        for poly in shapely_geom.geoms:
            patches.append(MplPolygon(list(poly.exterior.coords), closed=True))

fig, ax = plt.subplots(figsize=(8,8))
ax.add_collection(PatchCollection(patches, facecolor='red', edgecolor='darkred', alpha=0.7))

coords = roi.getInfo()['coordinates'][0]
min_lon, min_lat = coords[0]
max_lon, max_lat = coords[2]
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Roads')
plt.show()
