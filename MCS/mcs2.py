import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import random
import time
import requests
import json
from scipy.stats import gaussian_kde
from scipy.interpolate import griddata
import pickle
import csv

# ======================
# Configuration
# ======================
NUM_BOTS = 250
FPS = 30
SPEED_RANGE = (3, 7)
MARKER_SIZE = 5
ALPHA = 0.6
SIMULATION_TIME = 1
ELEVATION_PREFERENCE = 0.85
AGE_RANGE = (0.1, 2.0)
AGE_SPEED_FACTOR = 2.0

# Terrain behavior weights (subtle influence)
RIVER_ATTRACTION = 0.15
ROAD_ATTRACTION = 0.12
FOREST_AVOIDANCE = 0.08
ELEVATION_WEIGHT = 0.1

TERRAIN_COLORS = {
    'sparse_forest': np.array([144, 238, 144]) / 255,
    'dense_forest': np.array([0, 100, 0]) / 255,
    'water': np.array([0, 102, 204]) / 255,
    'road': np.array([51, 51, 51]) / 255,
}

# ======================
# Helper functions
# ======================
def color_distance(c1, c2):
    return np.linalg.norm(c1 - c2)

def closest_terrain_color(pixel_color):
    distances = {terrain: color_distance(pixel_color, color) for terrain, color in TERRAIN_COLORS.items()}
    return min(distances, key=distances.get)

def fetch_elevation_data(lat_center, lon_center, width_pixels, height_pixels, resolution_meters=30):
    print("Fetching elevation data...")
    lat_per_meter = 1 / 111000
    lon_per_meter = 1 / (111000 * np.cos(np.radians(lat_center)))

    width_meters = width_pixels * resolution_meters
    height_meters = height_pixels * resolution_meters

    lat_span = height_meters * lat_per_meter
    lon_span = width_meters * lon_per_meter

    lat_min = lat_center - lat_span / 2
    lat_max = lat_center + lat_span / 2
    lon_min = lon_center - lon_span / 2
    lon_max = lon_center + lon_span / 2

    grid_resolution = max(1, min(width_pixels, height_pixels) // 50)
    lats = np.linspace(lat_max, lat_min, height_pixels // grid_resolution)
    lons = np.linspace(lon_min, lon_max, width_pixels // grid_resolution)

    elevation_points, locations = [], []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            locations.append(f"{lat},{lon}")
            elevation_points.append((j * grid_resolution, i * grid_resolution))

    batch_size = 100
    all_elevations = []

    for i in range(0, len(locations), batch_size):
        batch = locations[i:i+batch_size]
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={'|'.join(batch)}"

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                elevations = [result['elevation'] for result in data['results']]
                all_elevations.extend(elevations)
                print(f"Fetched elevations batch {i//batch_size + 1}")
                time.sleep(0.5)
            else:
                all_elevations.extend(np.random.uniform(0, 100, len(batch)))
        except Exception:
            all_elevations.extend(np.random.uniform(0, 100, len(batch)))

    if len(all_elevations) == len(elevation_points):
        x_coords = [pt[0] for pt in elevation_points]
        y_coords = [pt[1] for pt in elevation_points]

        xi, yi = np.arange(width_pixels), np.arange(height_pixels)
        xi_grid, yi_grid = np.meshgrid(xi, yi)

        elevation_grid = griddata(
            (x_coords, y_coords),
            all_elevations,
            (xi_grid, yi_grid),
            method='linear',
            fill_value=np.mean(all_elevations)
        )
        print(f"Elevation range: {np.min(elevation_grid):.1f}–{np.max(elevation_grid):.1f} m")
        return elevation_grid

    print("Elevation mismatch → fallback random")
    return np.random.uniform(0, 100, (height_pixels, width_pixels))

# ======================
# SwarmBot Simulation
# ======================
class SwarmBot:
    def __init__(self, image_path='image.png', lat_center=40.7128, lon_center=-74.0060):
        self.image = Image.open(image_path).convert('RGB')
        self.width, self.height = self.image.size
        self.background = np.array(self.image)
        self.elevation_data = fetch_elevation_data(lat_center, lon_center, self.width, self.height)
        
        # Precompute terrain classification
        self.terrain_map = self._classify_terrain()
        
        # Precompute elevation gradients for navigation
        self.elevation_gradient = self._compute_elevation_gradient()

        self.bots = []
        cx, cy = self.width // 2, self.height // 2

        for _ in range(NUM_BOTS):
            angle = random.uniform(0, 2 * np.pi)
            radius = random.uniform(0, min(self.width, self.height) / 4)
            x, y = cx + radius * np.cos(angle), cy + radius * np.sin(angle)

            move_angle = random.uniform(0, 2 * np.pi)
            base_speed = random.uniform(*SPEED_RANGE)
            age = random.uniform(*AGE_RANGE)
            speed_mult = AGE_SPEED_FACTOR * (1.1 - age)
            speed = base_speed * speed_mult

            if age < 0.4:
                colors = [[1,0,0],[1,0.5,0],[1,1,0]]
            elif age < 0.7:
                colors = [[0.8,0.2,0.2],[0.8,0.4,0.1],[0.7,0.7,0.2]]
            else:
                colors = [[0.6,0.3,0.3],[0.6,0.4,0.2],[0.5,0.5,0.3]]

            self.bots.append({
                'x': x, 'y': y, 'angle': move_angle,
                'speed': speed, 'age': age,
                'base_speed': base_speed,
                'color': random.choice(colors)
            })

    def _classify_terrain(self):
        """Classify each pixel by terrain type"""
        terrain_map = np.zeros((self.height, self.width), dtype=int)
        # 0: sparse_forest, 1: dense_forest, 2: water, 3: road
        
        for y in range(self.height):
            for x in range(self.width):
                pixel = self.background[y, x] / 255.0
                terrain_type = closest_terrain_color(pixel)
                terrain_map[y, x] = list(TERRAIN_COLORS.keys()).index(terrain_type)
        
        return terrain_map

    def _compute_elevation_gradient(self):
        """Compute elevation gradient for downhill preference"""
        gy, gx = np.gradient(self.elevation_data)
        return np.stack([gx, gy], axis=-1)

    def _get_terrain_influence(self, x, y, current_angle):
        """Calculate terrain-based movement influence"""
        x_int, y_int = int(np.clip(x, 0, self.width - 1)), int(np.clip(y, 0, self.height - 1))
        
        # Sample surrounding area for terrain features
        sample_radius = 5
        x_min = max(0, x_int - sample_radius)
        x_max = min(self.width, x_int + sample_radius + 1)
        y_min = max(0, y_int - sample_radius)
        y_max = min(self.height, y_int + sample_radius + 1)
        
        terrain_patch = self.terrain_map[y_min:y_max, x_min:x_max]
        
        # Find direction to nearest water (rivers)
        water_mask = (terrain_patch == 2)
        if np.any(water_mask):
            water_coords = np.where(water_mask)
            # Get centroid of water in patch
            water_center_y = np.mean(water_coords[0]) + y_min - y_int
            water_center_x = np.mean(water_coords[1]) + x_min - x_int
            water_angle = np.arctan2(water_center_y, water_center_x)
            water_influence = RIVER_ATTRACTION * np.array([np.cos(water_angle), np.sin(water_angle)])
        else:
            water_influence = np.array([0.0, 0.0])
        
        # Find direction to nearest road
        road_mask = (terrain_patch == 3)
        if np.any(road_mask):
            road_coords = np.where(road_mask)
            road_center_y = np.mean(road_coords[0]) + y_min - y_int
            road_center_x = np.mean(road_coords[1]) + x_min - x_int
            road_angle = np.arctan2(road_center_y, road_center_x)
            road_influence = ROAD_ATTRACTION * np.array([np.cos(road_angle), np.sin(road_angle)])
        else:
            road_influence = np.array([0.0, 0.0])
        
        # Avoid dense forest
        forest_mask = (terrain_patch == 1)
        if np.any(forest_mask):
            forest_coords = np.where(forest_mask)
            forest_center_y = np.mean(forest_coords[0]) + y_min - y_int
            forest_center_x = np.mean(forest_coords[1]) + x_min - x_int
            forest_angle = np.arctan2(forest_center_y, forest_center_x)
            # Push away from forest
            forest_influence = -FOREST_AVOIDANCE * np.array([np.cos(forest_angle), np.sin(forest_angle)])
        else:
            forest_influence = np.array([0.0, 0.0])
        
        # Elevation influence (go downhill)
        elevation_grad = self.elevation_gradient[y_int, x_int]
        elevation_influence = -ELEVATION_WEIGHT * elevation_grad / (np.linalg.norm(elevation_grad) + 1e-6)
        
        return water_influence + road_influence + forest_influence + elevation_influence

    # ------------------
    # Core Simulation
    # ------------------
    def run_simulation(self):
        print("Running simulation...")
        total_frames = SIMULATION_TIME * FPS
        sensing_radius = 3
        for frame in range(total_frames):
            if frame % 30 == 0:
                print(f"Progress {100*frame/total_frames:.1f}%")
            self.update_bots_with_terrain(sensing_radius)
        print("Simulation complete")
        self.create_density_map()

    def update_bots_with_terrain(self, sensing_radius):
        for bot in self.bots:
            x_int, y_int = int(bot['x']), int(bot['y'])
            x_int = np.clip(x_int, 0, self.width - 1)
            y_int = np.clip(y_int, 0, self.height - 1)

            # Get terrain influence
            terrain_force = self._get_terrain_influence(bot['x'], bot['y'], bot['angle'])
            
            # Convert current angle to direction vector
            current_dir = np.array([np.cos(bot['angle']), np.sin(bot['angle'])])
            
            # Blend current direction with terrain influence
            influence_strength = 0.3 * (2.0 - bot['age'])  # Younger bots more influenced
            new_dir = current_dir + influence_strength * terrain_force
            new_dir = new_dir / (np.linalg.norm(new_dir) + 1e-6)
            
            # Update angle with some smoothing
            target_angle = np.arctan2(new_dir[1], new_dir[0])
            angle_diff = target_angle - bot['angle']
            # Normalize angle difference to [-π, π]
            angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi
            bot['angle'] += 0.1 * angle_diff
            
            # Add some random drift (age-adjusted)
            bot['angle'] += random.uniform(-0.02, 0.02) * (1 - bot['age'] * 0.3)

            # Move bot
            bot['x'] += np.cos(bot['angle']) * bot['speed']
            bot['y'] += np.sin(bot['angle']) * bot['speed']

            # Wrap boundaries
            bot['x'] %= self.width
            bot['y'] %= self.height

    # ------------------
    # Visualization & Saving
    # ------------------
    def create_density_map(self):
        positions = np.array([[b['x'], b['y']] for b in self.bots])
        
        # Create higher resolution density map
        x_grid = np.linspace(0, self.width, 150)
        y_grid = np.linspace(0, self.height, 150)
        xx, yy = np.meshgrid(x_grid, y_grid)
        grid_positions = np.vstack([xx.ravel(), yy.ravel()])

        kde = gaussian_kde(positions.T)
        density = kde(grid_positions).reshape(150, 150)

        self.save_distribution_data(positions, density, x_grid, y_grid)

        fig, axes = plt.subplots(2, 3, figsize=(24, 16))

        # Original background with final positions
        axes[0,0].imshow(self.background)
        axes[0,0].scatter(positions[:,0], positions[:,1], c='red', s=MARKER_SIZE, alpha=ALPHA)
        axes[0,0].set_title("Final Bot Positions")

        # Density map
        im1 = axes[0,1].imshow(density, extent=[0,self.width,self.height,0], cmap='hot')
        axes[0,1].set_title("Bot Density Map")
        plt.colorbar(im1, ax=axes[0,1])

        # Terrain classification overlay
        terrain_colors = np.zeros((self.height, self.width, 3))
        for i in range(self.height):
            for j in range(self.width):
                terrain_type = self.terrain_map[i, j]
                if terrain_type == 2:  # water - blue
                    terrain_colors[i, j] = [0, 0.5, 1]
                elif terrain_type == 3:  # road - gray
                    terrain_colors[i, j] = [0.5, 0.5, 0.5]
                elif terrain_type == 1:  # dense forest - dark green
                    terrain_colors[i, j] = [0, 0.4, 0]
                else:  # sparse forest - light green
                    terrain_colors[i, j] = [0.6, 0.8, 0.6]
        
        axes[0,2].imshow(terrain_colors)
        axes[0,2].scatter(positions[:,0], positions[:,1], c='red', s=MARKER_SIZE, alpha=0.8)
        axes[0,2].set_title("Terrain Classification + Bots")

        # Elevation map
        im2 = axes[1,0].imshow(self.elevation_data, extent=[0,self.width,self.height,0], cmap='terrain')
        axes[1,0].set_title("Elevation Map")
        plt.colorbar(im2, ax=axes[1,0])

        # Elevation + density overlay
        axes[1,1].imshow(self.elevation_data, extent=[0,self.width,self.height,0], cmap='terrain', alpha=0.6)
        im3 = axes[1,1].imshow(density, extent=[0,self.width,self.height,0], cmap='Reds', alpha=0.6)
        axes[1,1].set_title("Elevation + Density")

        # Movement trails (if we have history)
        axes[1,2].imshow(self.background, alpha=0.7)
        if hasattr(self, 'position_history') and len(self.position_history) > 1:
            # Show trails for subset of bots
            trail_bots = range(0, NUM_BOTS, max(1, NUM_BOTS//20))  # Show 20 trails max
            colors = plt.cm.Set3(np.linspace(0, 1, len(trail_bots)))
            
            for i, bot_idx in enumerate(trail_bots):
                trail_x = [pos[bot_idx, 0] for pos in self.position_history]
                trail_y = [pos[bot_idx, 1] for pos in self.position_history]
                axes[1,2].plot(trail_x, trail_y, color=colors[i], alpha=0.7, linewidth=2)
        
        axes[1,2].scatter(positions[:,0], positions[:,1], c='red', s=MARKER_SIZE*2, alpha=0.9, edgecolors='white')
        axes[1,2].set_title("Movement Trails")

        plt.tight_layout()
        ts = time.strftime("%Y%m%d_%H%M%S")
        fig.savefig(f"terrain_swarm_analysis_{ts}.png", dpi=300)
        print(f"Saved figure terrain_swarm_analysis_{ts}.png")
        plt.show()

    def save_distribution_data(self, positions, density, x_grid, y_grid):
        ts = time.strftime("%Y%m%d_%H%M%S")
        with open(f"bot_positions_{ts}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id','x','y','age','speed'])
            for i, b in enumerate(self.bots):
                writer.writerow([i,b['x'],b['y'],b['age'],b['speed']])
        np.save(f"density_grid_{ts}.npy", density)
        np.save(f"grid_coordinates_{ts}.npy", {'x_grid':x_grid,'y_grid':y_grid,'density':density})
        with open(f"swarm_data_{ts}.pkl","wb") as f:
            pickle.dump({'positions':positions,'density':density,'bots':self.bots}, f)

# ======================
# Run
# ======================
if __name__ == "__main__":
    sim = SwarmBot("imagebig.png")
    sim.run_simulation()