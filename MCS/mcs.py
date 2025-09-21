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

# Configuration
NUM_BOTS = 10  # Number of bots
FPS = 30  # Frames per second for animation
SPEED_RANGE = (1, 5)  # Min/max speed
MARKER_SIZE = 15  # Size of dots (smaller due to many bots)
ALPHA = 0.6  # Transparency of dots
SIMULATION_TIME = 5  # Simulation duration in seconds
ELEVATION_PREFERENCE = 0.65  # 65% chance to move toward lower elevation
AGE_RANGE = (0.1, 1.0)  # Age range (0.1 = young/fast, 1.0 = old/slow)
AGE_SPEED_FACTOR = 2.0  # How much age affects speed (higher = more effect)

# Define RGB colors normalized (0-1) for the terrain types
TERRAIN_COLORS = {
    'sparse_forest': np.array([144, 238, 144]) / 255,  # #90EE90 light green
    'dense_forest': np.array([0, 100, 0]) / 255,       # #006400 dark green
    'water': np.array([0, 102, 204]) / 255,            # #0066CC blue
    'road': np.array([51, 51, 51]) / 255,              # #333333 dark gray
}

def color_distance(c1, c2):
    """Calculate Euclidean distance between two RGB colors."""
    return np.linalg.norm(c1 - c2)

def closest_terrain_color(pixel_color):
    """Return the terrain type whose color is closest to the pixel color."""
    distances = {terrain: color_distance(pixel_color, color) for terrain, color in TERRAIN_COLORS.items()}
    closest = min(distances, key=distances.get)
    return closest

def fetch_elevation_data(lat_center, lon_center, width_pixels, height_pixels, resolution_meters=30):
    """
    Fetch elevation data for a grid around the center coordinates.
    
    Args:
        lat_center, lon_center: Center coordinates
        width_pixels, height_pixels: Image dimensions in pixels
        resolution_meters: Approximate resolution in meters per pixel
    
    Returns:
        2D numpy array of elevation data matching image dimensions
    """
    print("Fetching elevation data...")
    
    # Calculate the geographic bounds (rough approximation)
    # 1 degree latitude ≈ 111,000 meters
    # 1 degree longitude ≈ 111,000 * cos(latitude) meters
    lat_per_meter = 1 / 111000
    lon_per_meter = 1 / (111000 * np.cos(np.radians(lat_center)))
    
    # Calculate bounds
    width_meters = width_pixels * resolution_meters
    height_meters = height_pixels * resolution_meters
    
    lat_span = height_meters * lat_per_meter
    lon_span = width_meters * lon_per_meter
    
    lat_min = lat_center - lat_span / 2
    lat_max = lat_center + lat_span / 2
    lon_min = lon_center - lon_span / 2
    lon_max = lon_center + lon_span / 2
    
    # Create a grid of points to sample (reduce density to avoid API limits)
    grid_resolution = max(1, min(width_pixels, height_pixels) // 50)  # Sample every N pixels
    lats = np.linspace(lat_max, lat_min, height_pixels // grid_resolution)  # Flip for image coordinates
    lons = np.linspace(lon_min, lon_max, width_pixels // grid_resolution)
    
    elevation_points = []
    locations = []
    
    # Prepare locations for API call
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            locations.append(f"{lat},{lon}")
            elevation_points.append((j * grid_resolution, i * grid_resolution))  # Store pixel coordinates
    
    # Split into batches to avoid API limits (max ~100 points per request)
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
                print(f"Fetched elevations for batch {i//batch_size + 1}/{(len(locations)-1)//batch_size + 1}")
                time.sleep(0.5)  # Be nice to the API
            else:
                print(f"API error: {response.status_code}")
                # Fill with random elevations as fallback
                all_elevations.extend(np.random.uniform(0, 100, len(batch)))
        except Exception as e:
            print(f"Error fetching elevation data: {e}")
            # Fill with random elevations as fallback
            all_elevations.extend(np.random.uniform(0, 100, len(batch)))
    
    # Create the elevation grid by interpolating
    if len(all_elevations) == len(elevation_points):
        # Prepare data for interpolation
        x_coords = [point[0] for point in elevation_points]
        y_coords = [point[1] for point in elevation_points]
        
        # Create full resolution grid
        xi = np.arange(width_pixels)
        yi = np.arange(height_pixels)
        xi_grid, yi_grid = np.meshgrid(xi, yi)
        
        # Interpolate to full resolution
        elevation_grid = griddata(
            (x_coords, y_coords), 
            all_elevations,
            (xi_grid, yi_grid),
            method='linear',
            fill_value=np.mean(all_elevations)
        )
        
        print(f"Elevation range: {np.min(elevation_grid):.1f}m to {np.max(elevation_grid):.1f}m")
        return elevation_grid
    else:
        print("Error: Mismatch in elevation data, using random elevations")
        return np.random.uniform(0, 100, (height_pixels, width_pixels))

class SwarmBot:
    def __init__(self, image_path='image.png', lat_center=40.7128, lon_center=-74.0060):
        # Load and convert the SAR image
        self.image = Image.open(image_path).convert('RGB')
        self.width, self.height = self.image.size
        
        # Convert PIL image to numpy array
        self.background = np.array(self.image)
        
        # Fetch elevation data
        self.elevation_data = fetch_elevation_data(lat_center, lon_center, self.width, self.height)
        
        # Initialize bot swarm with random positions, angles, and speeds
        self.bots = []
        center_x, center_y = self.width // 2, self.height // 2
        
        for _ in range(NUM_BOTS):
            # Random starting position in a circle around center
            angle = random.uniform(0, 2 * np.pi)
            radius = random.uniform(0, min(self.width, self.height) / 4)
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            
            # Random movement parameters
            move_angle = random.uniform(0, 2 * np.pi)
            base_speed = random.uniform(*SPEED_RANGE)
            
            # Age affects speed: younger bots (lower age) move faster
            age = random.uniform(*AGE_RANGE)
            # Speed multiplier: young bots (age ~0.1) get ~2x speed, old bots (age ~1.0) get ~0.5x speed
            speed_multiplier = AGE_SPEED_FACTOR * (1.1 - age)  # Range roughly 0.2 to 2.0
            speed = base_speed * speed_multiplier
            
            # Generate colors based on age: younger = more vibrant, older = more muted
            if age < 0.4:  # Young bots - bright colors
                colors = [
                    [1.0, 0.0, 0.0],  # Bright Red
                    [1.0, 0.5, 0.0],  # Bright Orange
                    [1.0, 1.0, 0.0],  # Bright Yellow
                ]
            elif age < 0.7:  # Middle-aged bots - medium colors
                colors = [
                    [0.8, 0.2, 0.2],  # Medium Red
                    [0.8, 0.4, 0.1],  # Medium Orange
                    [0.7, 0.7, 0.2],  # Medium Yellow
                ]
            else:  # Older bots - muted colors
                colors = [
                    [0.6, 0.3, 0.3],  # Muted Red
                    [0.6, 0.4, 0.2],  # Muted Orange
                    [0.5, 0.5, 0.3],  # Muted Yellow
                ]
            
            bot = {
                'x': x,
                'y': y,
                'angle': move_angle,
                'speed': speed,
                'age': age,
                'base_speed': base_speed,
                'color': random.choice(colors)
            }
            self.bots.append(bot)
        
        # Create figure and axis for animation and visualization
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        # Show background image
        self.img = self.ax.imshow(self.background)

        # Scatter for bot markers
        colors = [bot['color'] for bot in self.bots]
        self.dots = self.ax.scatter(
            [bot['x'] for bot in self.bots],
            [bot['y'] for bot in self.bots],
            c=colors,
            s=MARKER_SIZE,
            alpha=ALPHA,
            edgecolors='white',
            linewidths=0.3
        )

        plt.tight_layout()
    
    def get_elevation_gradient(self, x, y, sensing_radius=3):
        """
        Calculate the direction of steepest descent (lowest elevation) around a point.
        
        Returns:
            angle: Direction toward lowest elevation, or None if no clear direction
            elevation_diff: Difference between highest and lowest elevation in area
        """
        x_int, y_int = int(x), int(y)
        x_clipped = np.clip(x_int, 0, self.width - 1)
        y_clipped = np.clip(y_int, 0, self.height - 1)

        x_min = max(0, x_clipped - sensing_radius)
        x_max = min(self.width - 1, x_clipped + sensing_radius)
        y_min = max(0, y_clipped - sensing_radius)
        y_max = min(self.height - 1, y_clipped + sensing_radius)

        # Get elevation data for the sensing area
        elevation_patch = self.elevation_data[y_min:y_max + 1, x_min:x_max + 1]
        
        if elevation_patch.size == 0:
            return None, 0
        
        # Find the lowest point in the patch
        min_elevation = np.min(elevation_patch)
        max_elevation = np.max(elevation_patch)
        elevation_diff = max_elevation - min_elevation
        
        # If there's no significant elevation difference, return None
        if elevation_diff < 1.0:  # Less than 1 meter difference
            return None, elevation_diff
        
        # Find coordinates of lowest point relative to sensing area
        min_indices = np.where(elevation_patch == min_elevation)
        if len(min_indices[0]) == 0:
            return None, elevation_diff
            
        # Take the first minimum point if multiple exist
        rel_y, rel_x = min_indices[0][0], min_indices[1][0]
        
        # Convert back to absolute coordinates
        target_x = x_min + rel_x
        target_y = y_min + rel_y
        
        # Calculate angle from current position to lowest point
        dx = target_x - x
        dy = target_y - y
        
        if dx == 0 and dy == 0:
            return None, elevation_diff
        
        angle = np.arctan2(dy, dx)
        return angle, elevation_diff
    
    def analyze_water_shape(self, x, y, analysis_radius=10):
        """
        Analyze the shape of nearby water to determine if it's a circular lake or linear water feature.
        
        Returns:
            is_circular: True if water appears to be a circular lake
            water_edge_angle: Direction to follow water edge, or None
            water_coverage: Percentage of analysis area that is water
        """
        x_int, y_int = int(x), int(y)
        x_clipped = np.clip(x_int, 0, self.width - 1)
        y_clipped = np.clip(y_int, 0, self.height - 1)

        x_min = max(0, x_clipped - analysis_radius)
        x_max = min(self.width - 1, x_clipped + analysis_radius)
        y_min = max(0, y_clipped - analysis_radius)
        y_max = min(self.height - 1, y_clipped + analysis_radius)

        # Get terrain data for the analysis area
        analysis_pixels = self.background[y_min:y_max + 1, x_min:x_max + 1] / 255
        
        # Create a binary water mask
        water_mask = np.zeros(analysis_pixels.shape[:2], dtype=bool)
        for i in range(analysis_pixels.shape[0]):
            for j in range(analysis_pixels.shape[1]):
                terrain = closest_terrain_color(analysis_pixels[i, j])
                water_mask[i, j] = (terrain == 'water')
        
        if not np.any(water_mask):
            return False, None, 0.0
        
        water_coverage = np.sum(water_mask) / water_mask.size
        
        # If very little water, not significant enough to analyze
        if water_coverage < 0.1:  # Less than 10% water
            return False, None, water_coverage
        
        # Analyze water distribution pattern
        center_y, center_x = water_mask.shape[0] // 2, water_mask.shape[1] // 2
        
        # Calculate distances from center for all water pixels
        water_positions = np.where(water_mask)
        if len(water_positions[0]) == 0:
            return False, None, water_coverage
        
        water_y = water_positions[0] - center_y
        water_x = water_positions[1] - center_x
        distances = np.sqrt(water_x**2 + water_y**2)
        
        # Check for circular pattern
        if len(distances) > 5:  # Need enough points for analysis
            # Calculate circularity metrics
            mean_distance = np.mean(distances)
            std_distance = np.std(distances)
            
            # Circular lakes have low standard deviation in distance from center
            # and high water coverage in the center area
            circularity_score = 1.0 - (std_distance / (mean_distance + 1e-6))
            
            # Check if water forms a compact, roughly circular shape
            is_circular = (circularity_score > 0.7 and 
                          water_coverage > 0.4 and 
                          mean_distance < analysis_radius * 0.8)
            
            if is_circular:
                return True, None, water_coverage
        
        # If not circular, find edge direction for linear water features
        # Calculate the gradient of the water mask to find edges
        gy, gx = np.gradient(water_mask.astype(float))
        gradient_magnitude = np.sqrt(gx**2 + gy**2)
        
        # Find the strongest edge direction
        if np.max(gradient_magnitude) > 0:
            max_grad_idx = np.unravel_index(np.argmax(gradient_magnitude), gradient_magnitude.shape)
            edge_gy = gy[max_grad_idx]
            edge_gx = gx[max_grad_idx]
            
            # Direction perpendicular to the gradient (along the edge)
            edge_angle = np.arctan2(-edge_gx, edge_gy)  # Perpendicular to gradient
            
            # Convert to global coordinates
            global_angle = edge_angle
            return False, global_angle, water_coverage
        
        return False, None, water_coverage
    
    def get_water_edge_direction(self, x, y, current_angle, sensing_radius=5):
        """
        Get direction to follow water edge, avoiding going into water or away from it.
        
        Returns:
            edge_angle: Angle to follow the water edge
        """
        x_int, y_int = int(x), int(y)
        
        # Sample points around the bot to find water boundary
        angles = np.linspace(0, 2*np.pi, 16, endpoint=False)  # 16 directions
        water_directions = []
        
        for angle in angles:
            # Check point at sensing radius
            test_x = x + sensing_radius * np.cos(angle)
            test_y = y + sensing_radius * np.sin(angle)
            
            test_x_int = np.clip(int(test_x), 0, self.width - 1)
            test_y_int = np.clip(int(test_y), 0, self.height - 1)
            
            pixel_color = self.background[test_y_int, test_x_int] / 255
            terrain = closest_terrain_color(pixel_color)
            
            if terrain == 'water':
                water_directions.append(angle)
        
        if len(water_directions) == 0:
            return current_angle
        
        # Find the direction that keeps water to one side (edge following)
        water_directions = np.array(water_directions)
        
        # Calculate the mean direction of water
        mean_water_x = np.mean(np.cos(water_directions))
        mean_water_y = np.mean(np.sin(water_directions))
        mean_water_angle = np.arctan2(mean_water_y, mean_water_x)
        
        # Direction perpendicular to water direction (along the edge)
        edge_angle1 = mean_water_angle + np.pi/2
        edge_angle2 = mean_water_angle - np.pi/2
        
        # Choose the edge direction closest to current movement
        diff1 = abs(((edge_angle1 - current_angle + np.pi) % (2*np.pi)) - np.pi)
        diff2 = abs(((edge_angle2 - current_angle + np.pi) % (2*np.pi)) - np.pi)
        
        return edge_angle1 if diff1 < diff2 else edge_angle2
    
    def run_simulation(self):
        """Run the entire simulation without animation for faster execution"""
        print("Running simulation...")
        total_frames = SIMULATION_TIME * FPS
        
        # Pre-allocate arrays for better performance
        sensing_radius = 3
        
        for frame in range(total_frames):
            # Show progress every 30 frames (1 second)
            if frame % 30 == 0:
                progress = (frame / total_frames) * 100
                print(f"Progress: {progress:.1f}%")
            
            self.update_bots_fast(sensing_radius)
        
        print("Simulation complete! Creating analysis...")
        self.create_density_map()
    
    def update_bots_fast(self, sensing_radius):
        """Optimized bot update without animation overhead"""
        for bot in self.bots:
            x_int, y_int = int(bot['x']), int(bot['y'])
            x_clipped = np.clip(x_int, 0, self.width - 1)
            y_clipped = np.clip(y_int, 0, self.height - 1)

            x_min = max(0, x_clipped - sensing_radius)
            x_max = min(self.width - 1, x_clipped + sensing_radius)
            y_min = max(0, y_clipped - sensing_radius)
            y_max = min(self.height - 1, y_clipped + sensing_radius)

            # Get nearby terrain (optimized)
            nearby_pixels = self.background[y_min:y_max + 1, x_min:x_max + 1] / 255.0
            
            # Count terrain types more efficiently
            terrain_counts = {'water': 0, 'road': 0, 'sparse_forest': 0, 'dense_forest': 0}
            
            for i in range(nearby_pixels.shape[0]):
                for j in range(nearby_pixels.shape[1]):
                    pixel_color = nearby_pixels[i, j]
                    terrain = closest_terrain_color(pixel_color)
                    terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1

            # Check for water and analyze its shape
            is_circular_lake, water_edge_angle, water_coverage = self.analyze_water_shape(bot['x'], bot['y'])
            
            # Get elevation gradient
            elevation_angle, elevation_diff = self.get_elevation_gradient(bot['x'], bot['y'], sensing_radius)
            
            # Age affects movement characteristics
            age_factor = bot['age']
            angle_adjustment_factor = 1.0 - (age_factor * 0.3)
            age_elevation_preference = ELEVATION_PREFERENCE * (1.0 + (age_factor - 0.5) * 0.2)
            age_elevation_preference = np.clip(age_elevation_preference, 0.1, 0.9)
            
            # Decision making
            angle_adjust = 0
            behavior_used = "random"
            
            # Priority 1: Water edge following
            if (terrain_counts.get('water', 0) > 0 and 
                not is_circular_lake and 
                water_coverage > 0.15):
                
                edge_direction = self.get_water_edge_direction(bot['x'], bot['y'], bot['angle'])
                target_angle = edge_direction
                angle_diff = target_angle - bot['angle']
                
                # Normalize angle difference
                while angle_diff > np.pi:
                    angle_diff -= 2 * np.pi
                while angle_diff < -np.pi:
                    angle_diff += 2 * np.pi
                
                angle_adjust = angle_diff * 0.4 * angle_adjustment_factor
                behavior_used = "water_edge"
                
            # Priority 2: Elevation-based movement
            elif (elevation_angle is not None and 
                  elevation_diff > 1.0 and 
                  random.random() < age_elevation_preference):
                
                target_angle = elevation_angle
                angle_diff = target_angle - bot['angle']
                
                while angle_diff > np.pi:
                    angle_diff -= 2 * np.pi
                while angle_diff < -np.pi:
                    angle_diff += 2 * np.pi
                
                angle_adjust = angle_diff * 0.3 * angle_adjustment_factor
                behavior_used = "elevation"
                
            # Priority 3: Terrain-based navigation
            else:
                if terrain_counts.get('road', 0) > terrain_counts.get('water', 0):
                    angle_adjust += 0.5 * angle_adjustment_factor
                    behavior_used = "road_following"
                elif terrain_counts.get('water', 0) > terrain_counts.get('road', 0) and is_circular_lake:
                    angle_adjust -= 1.0 * angle_adjustment_factor
                    behavior_used = "avoid_lake"
                else:
                    behavior_used = "random"

            # Store behavior
            bot['behavior'] = behavior_used
            
            # Add random component
            random_component = random.uniform(-0.03, 0.03) * (1.0 - age_factor * 0.5)
            bot['angle'] += angle_adjust + random_component

            # Move the bot
            bot['x'] += np.cos(bot['angle']) * bot['speed']
            bot['y'] += np.sin(bot['angle']) * bot['speed']

            # Handle boundaries
            if bot['x'] < 0 or bot['x'] >= self.width:
                bot['x'] = bot['x'] % self.width
                bot['angle'] = random.uniform(0, 2 * np.pi)
            if bot['y'] < 0 or bot['y'] >= self.height:
                bot['y'] = bot['y'] % self.height
                bot['angle'] = random.uniform(0, 2 * np.pi)

    def update(self, frame):
        """Single animation frame update: advance bots and refresh scatter offsets."""
        sensing_radius = 3
        # Advance the simulation by one step
        self.update_bots_fast(sensing_radius)

        # Update scatter offsets
        xs = [bot['x'] for bot in self.bots]
        ys = [bot['y'] for bot in self.bots]
        self.dots.set_offsets(np.c_[xs, ys])

        return [self.dots]

    def create_density_map(self):
        """Create a 2D density map of bot positions and show elevation map"""
        positions = np.array([[bot['x'], bot['y']] for bot in self.bots])

        # Create a regular grid to evaluate density
        x_grid = np.linspace(0, self.width, 100)
        y_grid = np.linspace(0, self.height, 100)
        xx, yy = np.meshgrid(x_grid, y_grid)
        grid_positions = np.vstack([xx.ravel(), yy.ravel()])

        # Calculate density
        kde = gaussian_kde(positions.T)
        density = kde(grid_positions).reshape(100, 100)

        # Save distribution data in multiple formats
        self.save_distribution_data(positions, density, x_grid, y_grid)

        # ✅ Store fig and axes in self
        self.fig, self.axes = plt.subplots(2, 2, figsize=(20, 16))

        # Original image with final bot positions
        self.axes[0,0].imshow(self.background)
        self.axes[0,0].scatter([bot['x'] for bot in self.bots], 
                            [bot['y'] for bot in self.bots],
                            c='red', s=MARKER_SIZE, alpha=ALPHA)
        self.axes[0,0].set_title('Final Bot Positions')
        self.axes[0,0].set_xticks([])
        self.axes[0,0].set_yticks([])

        # Bot density map
        im1 = self.axes[0,1].imshow(density, extent=[0, self.width, self.height, 0],
                                    cmap='hot', interpolation='gaussian')
        self.axes[0,1].set_title('Bot Density Map')
        plt.colorbar(im1, ax=self.axes[0,1], label='Density')

        # Elevation map
        im2 = self.axes[1,0].imshow(self.elevation_data, extent=[0, self.width, self.height, 0],
                                    cmap='terrain', interpolation='bilinear')
        self.axes[1,0].set_title('Elevation Map (meters)')
        plt.colorbar(im2, ax=self.axes[1,0], label='Elevation (m)')

        # Combined view: elevation + final bot positions
        self.axes[1,1].imshow(self.elevation_data, extent=[0, self.width, self.height, 0],
                            cmap='terrain', alpha=0.7, interpolation='bilinear')
        self.axes[1,1].scatter([bot['x'] for bot in self.bots], 
                            [bot['y'] for bot in self.bots],
                            c='red', s=MARKER_SIZE*2, alpha=0.8, edgecolors='white')
        self.axes[1,1].set_title('Elevation Map + Final Bot Positions')

        plt.tight_layout()

        # Save the complete figure as an image
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.fig.savefig(f'swarm_analysis_{timestamp}.png', dpi=300, bbox_inches='tight')
        print(f"Saved complete analysis figure as: swarm_analysis_{timestamp}.png")

        plt.show()

    def save_distribution_data(self, positions, density, x_grid, y_grid):
        """Save distribution data in multiple formats for later use"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 1. Save raw bot positions as CSV
        positions_filename = f'bot_positions_{timestamp}.csv'
        with open(positions_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['bot_id', 'x', 'y', 'age', 'speed', 'behavior'])
            for i, bot in enumerate(self.bots):
                writer.writerow([i, bot['x'], bot['y'], bot['age'], bot['speed'], 
                            bot.get('behavior', 'unknown')])
        print(f"Saved bot positions as CSV: {positions_filename}")

        # 2. Save density grid as numpy array
        density_filename = f'density_grid_{timestamp}.npy'
        np.save(density_filename, density)
        print(f"Saved density grid as numpy array: {density_filename}")

        # 3. Save grid coordinates
        grid_filename = f'grid_coordinates_{timestamp}.npy'
        grid_data = {
            'x_grid': x_grid,
            'y_grid': y_grid,
            'density': density,
            'width': self.width,
            'height': self.height
        }
        np.save(grid_filename, grid_data)
        print(f"Saved grid coordinates: {grid_filename}")

        # 4. Save comprehensive data as pickle (easiest to reload everything)
        pickle_filename = f'swarm_data_{timestamp}.pkl'
        comprehensive_data = {
            'bot_positions': positions,
            'density_grid': density,
            'x_grid': x_grid,
            'y_grid': y_grid,
            'elevation_data': self.elevation_data,
            'background_image': self.background,
            'bots_data': self.bots,
            'image_dimensions': (self.width, self.height),
            'simulation_params': {
                'num_bots': NUM_BOTS,
                'simulation_time': SIMULATION_TIME,
                'elevation_preference': ELEVATION_PREFERENCE,
                'age_range': AGE_RANGE,
                'speed_range': SPEED_RANGE
            }
        }

        with open(pickle_filename, 'wb') as f:
            pickle.dump(comprehensive_data, f)
        print(f"Saved comprehensive data as pickle: {pickle_filename}")

        # 5. Save density as a high-resolution image
        density_img_filename = f'density_heatmap_{timestamp}.png'
        plt.figure(figsize=(12, 8))
        plt.imshow(density, extent=[0, self.width, self.height, 0],
                cmap='hot', interpolation='gaussian')
        plt.colorbar(label='Bot Density')
        plt.title('Bot Density Distribution')
        plt.xlabel('X Position (pixels)')
        plt.ylabel('Y Position (pixels)')
        plt.savefig(density_img_filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved density heatmap image: {density_img_filename}")

        # 6. Create a simple text summary
        summary_filename = f'simulation_summary_{timestamp}.txt'
        with open(summary_filename, 'w') as f:
            f.write(f"Swarm Bot Simulation Summary\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Number of bots: {NUM_BOTS}\n")
            f.write(f"Simulation time: {SIMULATION_TIME} seconds\n")
            f.write(f"Image dimensions: {self.width} x {self.height} pixels\n")
            f.write(f"Elevation preference: {ELEVATION_PREFERENCE}\n")
            f.write(f"Age range: {AGE_RANGE}\n")
            f.write(f"Speed range: {SPEED_RANGE}\n")
            f.write(f"\nFinal positions summary:\n")
            f.write(f"X range: {np.min(positions[:, 0]):.2f} to {np.max(positions[:, 0]):.2f}\n")
            f.write(f"Y range: {np.min(positions[:, 1]):.2f} to {np.max(positions[:, 1]):.2f}\n")
            f.write(f"Density grid size: {density.shape}\n")
            f.write(f"Max density: {np.max(density):.6f}\n")
            f.write(f"Min density: {np.min(density):.6f}\n")
        print(f"Saved simulation summary: {summary_filename}")

        print(f"\n--- Data Saving Complete ---")
        print(f"Files saved with timestamp: {timestamp}")
        print(f"To load data later, use:")
        print(f"  import pickle")
        print(f"  with open('{pickle_filename}', 'rb') as f:")
        print(f"      data = pickle.load(f)")
        print(f"  density = data['density_grid']")
        print(f"  positions = data['bot_positions']")

    def animate(self):
        # Create the animation with a fixed frame count so it ends cleanly
        total_frames = SIMULATION_TIME * FPS

        # Keep animation reference on the instance to avoid GC
        self.anim = FuncAnimation(
            self.fig,
            self.update,
            frames=total_frames,
            interval=1000 / FPS,
            blit=True,
            repeat=False,
            save_count=total_frames
        )

        # Show the animation; when the user closes the window or animation finishes,
        # plt.show() will return and we can proceed to create the density map.
        plt.show()

        # After animation ends, create and save density map and analysis
        try:
            self.create_density_map()
        except Exception as e:
            print(f"Error creating density map after animation: {e}")

# Create and run the animation
if __name__ == "__main__":
    try:
        # Default coordinates for New York City (you can change these)
        swarm = SwarmBot('image.png', lat_center=40.7128, lon_center=-74.0060)
        print(f"Image size: {swarm.width}x{swarm.height} pixels")
        print(f"Created swarm of {NUM_BOTS} bots")
        print(f"Running simulation for {SIMULATION_TIME} seconds...")
        print(f"Bots will prefer lower elevations {ELEVATION_PREFERENCE*100}% of the time (modified by age)")
        print(f"Age range: {AGE_RANGE[0]} to {AGE_RANGE[1]} (affects speed and behavior)")
        swarm.animate()
    except KeyboardInterrupt:
        print("\nAnimation stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()