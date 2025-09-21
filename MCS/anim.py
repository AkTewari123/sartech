import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PIL import Image
import random
import time
import requests
import json
from scipy.stats import gaussian_kde
from scipy.interpolate import griddata
import pickle
import csv
from numba import jit, njit
from scipy.ndimage import map_coordinates

# Configuration
# Removed NUM_BOTS from here to set it dynamically
FPS = 30
SPEED_RANGE = (1, 3)
MARKER_SIZE = 15
ALPHA = 0.6
ANIMATION_TIME = 10
ELEVATION_PREFERENCE = 0.65
AGE_RANGE = (0.1, 1.0)
AGE_SPEED_FACTOR = 2.0
SENSING_RADIUS = 3

# Pre-computed terrain colors as numpy arrays
TERRAIN_COLORS_ARRAY = np.array([
    [144, 238, 144],  # sparse_forest
    [0, 100, 0],      # dense_forest  
    [0, 102, 204],    # water
    [51, 51, 51]      # road
]) / 255.0

TERRAIN_NAMES = ['sparse_forest', 'dense_forest', 'water', 'road']

@njit
def fast_closest_terrain(pixel_rgb):
    """Numba-optimized terrain classification"""
    min_dist = 999.0
    closest_idx = 0
    
    for i in range(4):  # 4 terrain types
        dist = 0.0
        for j in range(3):  # RGB channels
            diff = pixel_rgb[j] - TERRAIN_COLORS_ARRAY[i, j]
            dist += diff * diff
        
        if dist < min_dist:
            min_dist = dist
            closest_idx = i
    
    return closest_idx

@njit
def update_bots_vectorized(bot_positions, bot_angles, bot_speeds, bot_ages, 
                          terrain_map, elevation_data, elevation_gradients,
                          width, height, sensing_radius, elevation_preference):
    """Highly optimized bot update using numba"""
    n_bots = len(bot_positions)
    
    for i in range(n_bots):
        x, y = bot_positions[i]
        x_int = max(0, min(width - 1, int(x)))
        y_int = max(0, min(height - 1, int(y)))
        
        # Fast terrain sampling
        x_min = max(0, x_int - sensing_radius)
        x_max = min(width, x_int + sensing_radius + 1)
        y_min = max(0, y_int - sensing_radius)  
        y_max = min(height, y_int + sensing_radius + 1)
        
        # Count terrain types in sensing area
        water_count = 0
        road_count = 0
        total_pixels = 0
        
        for yi in range(y_min, y_max):
            for xi in range(x_min, x_max):
                terrain_type = terrain_map[yi, xi]
                total_pixels += 1
                if terrain_type == 2:  # water
                    water_count += 1
                elif terrain_type == 3:  # road
                    road_count += 1
        
        # Age-based factors
        age_factor = bot_ages[i]
        angle_adjust_factor = 1.0 - (age_factor * 0.3)
        age_elev_pref = elevation_preference * (1.0 + (age_factor - 0.5) * 0.2)
        age_elev_pref = max(0.1, min(0.9, age_elev_pref))
        
        # Decision making
        angle_adjust = 0.0
        
        # Water edge following (simplified)
        if water_count > 0 and water_count < total_pixels * 0.8:
            # Follow water edge - simplified version
            if random.random() < 0.6:
                angle_adjust += np.random.uniform(-0.5, 0.5) * angle_adjust_factor
                
        # Road following
        elif road_count > water_count:
            angle_adjust += 0.3 * angle_adjust_factor
            
        # Elevation-based movement
        elif random.random() < age_elev_pref:
            grad_x = elevation_gradients[y_int, x_int, 0]
            grad_y = elevation_gradients[y_int, x_int, 1]
            
            if abs(grad_x) > 0.1 or abs(grad_y) > 0.1:
                target_angle = np.arctan2(-grad_y, -grad_x)  # Negative for downhill
                angle_diff = target_angle - bot_angles[i]
                
                # Normalize angle difference
                while angle_diff > np.pi:
                    angle_diff -= 2 * np.pi
                while angle_diff < -np.pi:
                    angle_diff += 2 * np.pi
                    
                angle_adjust = angle_diff * 0.3 * angle_adjust_factor
        
        # Add random component
        random_component = np.random.uniform(-0.03, 0.03) * (1.0 - age_factor * 0.5)
        bot_angles[i] += angle_adjust + random_component
        
        # Move bot
        bot_positions[i, 0] += np.cos(bot_angles[i]) * bot_speeds[i]
        bot_positions[i, 1] += np.sin(bot_angles[i]) * bot_speeds[i]
        
        # Handle boundaries (wrap around)
        if bot_positions[i, 0] < 0:
            bot_positions[i, 0] = width + bot_positions[i, 0]
        elif bot_positions[i, 0] >= width:
            bot_positions[i, 0] = bot_positions[i, 0] - width
            
        if bot_positions[i, 1] < 0:
            bot_positions[i, 1] = height + bot_positions[i, 1] 
        elif bot_positions[i, 1] >= height:
            bot_positions[i, 1] = bot_positions[i, 1] - height

def fetch_elevation_data_cached(lat_center, lon_center, width_pixels, height_pixels, 
                               resolution_meters=30, cache_file=None):
    """Optimized elevation fetching with caching"""
    
    # Try to load from cache first
    if cache_file:
        try:
            cached_data = np.load(cache_file, allow_pickle=True).item()
            if (cached_data['lat_center'] == lat_center and 
                cached_data['lon_center'] == lon_center and
                cached_data['width'] == width_pixels and
                cached_data['height'] == height_pixels):
                print("Using cached elevation data")
                return cached_data['elevation']
        except:
            print("No valid cache found, fetching new data")
    
    print("Fetching elevation data...")
    
    grid_resolution = max(2, min(width_pixels, height_pixels) // 25)
    
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
    
    lats = np.linspace(lat_max, lat_min, height_pixels // grid_resolution)
    lons = np.linspace(lon_min, lon_max, width_pixels // grid_resolution)
    
    elevation_points, locations = [], []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            locations.append(f"{lat},{lon}")
            elevation_points.append((j * grid_resolution, i * grid_resolution))
    
    batch_size = 200  
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
                print(f"Fetched batch {i//batch_size + 1}")
                time.sleep(0.3)
            else:
                all_elevations.extend(np.random.uniform(0, 100, len(batch)))
        except:
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
        
        if cache_file:
            cache_data = {
                'lat_center': lat_center,
                'lon_center': lon_center,
                'width': width_pixels,
                'height': height_pixels,
                'elevation': elevation_grid
            }
            np.save(cache_file, cache_data)
            print(f"Cached elevation data to {cache_file}")
        
        print(f"Elevation range: {np.min(elevation_grid):.1f}–{np.max(elevation_grid):.1f} m")
        return elevation_grid
    
    print("Using random elevation fallback")
    return np.random.uniform(0, 100, (height_pixels, width_pixels))

class OptimizedSwarmBot:
    def __init__(self, num_bots, image_path='image.png', lat_center=40.7128, lon_center=-74.0060):
        # Load and process image
        self.image = Image.open(image_path).convert('RGB')
        self.width, self.height = self.image.size
        self.background = np.array(self.image)
        self.num_bots = num_bots # Store num_bots
        
        print("Classifying terrain...")
        self.terrain_map = self._classify_terrain_vectorized()
        
        cache_file = f"elevation_cache_{lat_center}_{lon_center}_{self.width}x{self.height}.npy"
        self.elevation_data = fetch_elevation_data_cached(
            lat_center, lon_center, self.width, self.height, cache_file=cache_file
        )
        
        print("Computing elevation gradients...")
        gy, gx = np.gradient(self.elevation_data)
        self.elevation_gradients = np.stack([gx, gy], axis=-1)
        
        # Initialize bots as numpy arrays for better performance
        self.bot_positions = np.zeros((self.num_bots, 2))
        self.bot_angles = np.zeros(self.num_bots)
        self.bot_speeds = np.zeros(self.num_bots)
        self.bot_ages = np.zeros(self.num_bots)
        self.bot_colors = []
        
        center_x, center_y = self.width // 2, self.height // 2
        
        angles = np.random.uniform(0, 2*np.pi, self.num_bots)
        radii = np.random.uniform(0, min(self.width, self.height)/4, self.num_bots)
        
        self.bot_positions[:, 0] = center_x + radii * np.cos(angles)
        self.bot_positions[:, 1] = center_y + radii * np.sin(angles)
        
        self.bot_angles = np.random.uniform(0, 2*np.pi, self.num_bots)
        base_speeds = np.random.uniform(*SPEED_RANGE, self.num_bots)
        self.bot_ages = np.random.uniform(*AGE_RANGE, self.num_bots)
        
        speed_multipliers = AGE_SPEED_FACTOR * (1.1 - self.bot_ages)
        self.bot_speeds = base_speeds * speed_multipliers
        
        for age in self.bot_ages:
            if age < 0.4:
                colors = [[1.0, 0.0, 0.0], [1.0, 0.5, 0.0], [1.0, 1.0, 0.0]]
            elif age < 0.7:
                colors = [[0.8, 0.2, 0.2], [0.8, 0.4, 0.1], [0.7, 0.7, 0.2]]
            else:
                colors = [[0.6, 0.3, 0.3], [0.6, 0.4, 0.2], [0.5, 0.5, 0.3]]
            self.bot_colors.append(random.choice(colors))
    
    def _classify_terrain_vectorized(self):
        """Fast vectorized terrain classification"""
        terrain_map = np.zeros((self.height, self.width), dtype=np.uint8)
        
        chunk_size = 1000
        background_norm = self.background.astype(np.float32) / 255.0
        
        for y_start in range(0, self.height, chunk_size):
            y_end = min(y_start + chunk_size, self.height)
            
            for x_start in range(0, self.width, chunk_size):
                x_end = min(x_start + chunk_size, self.width)
                
                chunk = background_norm[y_start:y_end, x_start:x_end]
                
                for terrain_idx in range(4):
                    terrain_color = TERRAIN_COLORS_ARRAY[terrain_idx]
                    distances = np.sum((chunk - terrain_color)**2, axis=2)
                    
                    if terrain_idx == 0:
                        min_distances = distances
                        terrain_map[y_start:y_end, x_start:x_end] = 0
                    else:
                        mask = distances < min_distances
                        terrain_map[y_start:y_end, x_start:x_end][mask] = terrain_idx
                        min_distances = np.minimum(min_distances, distances)
        
        return terrain_map

    def animate_simulation(self):
        """Runs the simulation with a real-time animation."""
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(self.background)
        ax.set_title("Swarm Simulation")
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Plot the bots initially
        scat = ax.scatter(self.bot_positions[:, 0], self.bot_positions[:, 1],
                          c=self.bot_colors, s=MARKER_SIZE, alpha=ALPHA)
        
        frame_count = 0

        def update(frame):
            nonlocal frame_count
            frame_count += 1
            
            # Use the optimized update function
            update_bots_vectorized(
                self.bot_positions, self.bot_angles, self.bot_speeds, self.bot_ages,
                self.terrain_map, self.elevation_data, self.elevation_gradients,
                self.width, self.height, SENSING_RADIUS, ELEVATION_PREFERENCE
            )
            
            # Update the scatter plot data
            scat.set_offsets(self.bot_positions)
            
            # Update the title with the current frame count
            ax.set_title(f"Swarm Simulation - {self.num_bots} Bots - Frame {frame_count}")
            
            return [scat]

        # Use FuncAnimation for real-time plotting
        ani = FuncAnimation(fig, update, frames=int(ANIMATION_TIME * FPS), 
                            interval=1000/FPS, blit=True)
        
        plt.show()

if __name__ == "__main__":
    bot_counts = [25, 200, 600]
    for count in bot_counts:
        try:
            print(f"\n--- Starting animated simulation with {count} bots for {ANIMATION_TIME} seconds... ---")
            
            swarm = OptimizedSwarmBot(num_bots=count, image_path='image.png', lat_center=40.7128, lon_center=-74.0060)
            
            start_time = time.time()
            swarm.animate_simulation()
            end_time = time.time()
            
            print(f"Total animation time for {count} bots: {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            print(f"Error with {count} bots: {e}")
            import traceback
            traceback.print_exc()