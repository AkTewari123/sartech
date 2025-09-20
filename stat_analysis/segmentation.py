import ee

# Initialize Earth Engine with your project
ee.Initialize(project='sartech-api')

# --- 1. Define region of interest ---
# Rectangle coordinates: [min_lon, min_lat, max_lon, max_lat]
roi = ee.Geometry.Rectangle([-74.2, 40.7, -74.1, 40.75])  # Example

# --- 2. Load water dataset ---
water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')

# Mask water pixels where water occurs > 0%
water_mask = water.gt(0).selfMask()

# Clip to ROI
water_roi = water_mask.clip(roi)

# --- 3. Convert raster water pixels to vector polygons ---
water_polygons = water_roi.reduceToVectors(
    geometry=roi,
    scale=30,               # 30m resolution
    geometryType='polygon',
    eightConnected=True,    # pixels touching diagonally are connected
    labelProperty='water',  # property name
    maxPixels=1e10
)

# --- 4. Print some info ---
print("Number of river polygons:", water_polygons.size().getInfo())
print("Example polygon coordinates:", water_polygons.first().geometry().getInfo())

# --- 5. Export as GeoJSON to Google Drive ---
export = ee.batch.Export.table.toDrive(
    collection=water_polygons,
    description='river_polygons',
    folder='EarthEngineExports',
    fileFormat='GeoJSON'
)

export.start()
print("Export started. Check your Google Drive folder 'EarthEngineExports'.")
