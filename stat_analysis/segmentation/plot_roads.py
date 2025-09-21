import requests
import matplotlib.pyplot as plt

# ====== 1. Define bounding box ======
# Format: south,west,north,east
# This box covers a suburban area around Princeton University
bbox = "36.460,-116.950,36.600,-116.800"   # Princeton, NJ

# ====== 2. Query OpenStreetMap Overpass API ======
overpass_url = "https://overpass-api.de/api/interpreter"
query = f"""
[out:json];
way["highway"]({bbox});
(._;>;);
out geom;
"""
response = requests.get(overpass_url, params={"data": query})
data = response.json()

# ====== 3. Extract road coordinate sequences ======
roads = []
for element in data["elements"]:
    if element["type"] == "way" and "geometry" in element:
        coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
        roads.append(coords)

# ====== 4. Plot with Matplotlib ======
fig, ax = plt.subplots(figsize=(10, 10))
for road in roads:
    lons, lats = zip(*road)
    ax.plot(lons, lats, color="gray", linewidth=4)  # <-- 10 px thick

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Princeton, NJ Suburban Roads (OSM)")
plt.show()
