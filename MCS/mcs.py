import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PIL import Image
import random
import time
from scipy.stats import gaussian_kde

# Configuration
NUM_BOTS = 300  # Number of bots
FPS = 30  # Frames per second for animation
SPEED_RANGE = (1, 5)  # Min/max speed
MARKER_SIZE = 5  # Size of dots (smaller due to many bots)
ALPHA = 0.6  # Transparency of dots
SIMULATION_TIME = 5  # Simulation duration in seconds

class SwarmBot:
    def __init__(self, image_path='./sar.png'):
        # Load and convert the SAR image
        self.image = Image.open(image_path).convert('RGB')
        self.width, self.height = self.image.size
        
        # Convert PIL image to numpy array
        self.background = np.array(self.image)
        
        # Create the figure and axis
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # Create the image display
        self.img = self.ax.imshow(self.background)
        
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
            speed = random.uniform(*SPEED_RANGE)
            
            # Generate colors: bright red, orange, yellow for better visibility
            colors = [
                [1.0, 0.0, 0.0],  # Red
                [1.0, 0.5, 0.0],  # Orange
                [1.0, 1.0, 0.0],  # Yellow
            ]
            bot = {
                'x': x,
                'y': y,
                'angle': move_angle,
                'speed': speed,
                'color': random.choice(colors)  # Pick one of the bright colors
            }
            self.bots.append(bot)
        
        # Create scatter plot for all bots
        colors = [bot['color'] for bot in self.bots]
        self.dots = self.ax.scatter(
            [bot['x'] for bot in self.bots],
            [bot['y'] for bot in self.bots],
            c=colors,
            s=MARKER_SIZE,
            alpha=ALPHA,
            edgecolors='white',
            linewidths=0.5
        )
        
        plt.tight_layout()
    
    def update(self, frame):
        new_positions = [], []
        
        for bot in self.bots:
            # Update position based on angle and speed
            bot['x'] += np.cos(bot['angle']) * bot['speed']
            bot['y'] += np.sin(bot['angle']) * bot['speed']
            
            # Wrap around screen edges with small random angle change
            if bot['x'] < 0 or bot['x'] >= self.width:
                bot['x'] = bot['x'] % self.width
                bot['angle'] = random.uniform(0, 2 * np.pi)
            if bot['y'] < 0 or bot['y'] >= self.height:
                bot['y'] = bot['y'] % self.height
                bot['angle'] = random.uniform(0, 2 * np.pi)
            
            # Small random angle adjustments for organic movement
            bot['angle'] += random.uniform(-0.1, 0.1)
            
            new_positions[0].append(bot['x'])
            new_positions[1].append(bot['y'])
        
        # Update all dot positions at once
        self.dots.set_offsets(np.c_[new_positions[0], new_positions[1]])
        
        return [self.dots]
    
    def create_density_map(self):
        """Create a 2D density map of bot positions"""
        positions = np.array([[bot['x'], bot['y']] for bot in self.bots])
        
        # Create a regular grid to evaluate density
        x_grid = np.linspace(0, self.width, 100)
        y_grid = np.linspace(0, self.height, 100)
        xx, yy = np.meshgrid(x_grid, y_grid)
        grid_positions = np.vstack([xx.ravel(), yy.ravel()])
        
        # Calculate density
        kde = gaussian_kde(positions.T)
        density = kde(grid_positions).reshape(100, 100)
        
        # Create density plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Original image with final bot positions
        ax1.imshow(self.background)
        ax1.scatter([bot['x'] for bot in self.bots], 
                   [bot['y'] for bot in self.bots],
                   c='red', s=MARKER_SIZE, alpha=ALPHA)
        ax1.set_title('Final Bot Positions')
        
        # Density map
        im = ax2.imshow(density, extent=[0, self.width, self.height, 0],
                       cmap='hot', interpolation='gaussian')
        ax2.set_title('Bot Density Map')
        plt.colorbar(im, ax=ax2, label='Density')
        
        plt.tight_layout()
        plt.show()

    def animate(self):
        # Create the animation with frame limit for 30 seconds
        total_frames = SIMULATION_TIME * FPS
        frame_count = 0
        
        def animation_update(frame):
            nonlocal frame_count
            frame_count += 1
            result = self.update(frame)
            
            # Stop after 30 seconds
            if frame_count >= total_frames:
                plt.close()
                self.create_density_map()
            
            return result
        
        # Create the animation
        anim = FuncAnimation(
            self.fig,
            animation_update,
            frames=None,
            interval=1000/FPS,
            blit=True
        )
        
        # Show the animation
        plt.show()

# Create and run the animation
try:
    swarm = SwarmBot('./sar.png')
    print(f"Image size: {swarm.width}x{swarm.height} pixels")
    print(f"Created swarm of {NUM_BOTS} bots")
    print(f"Running simulation for {SIMULATION_TIME} seconds...")
    swarm.animate()
except KeyboardInterrupt:
    print("\nAnimation stopped by user")
except Exception as e:
    print(f"Error: {e}")