import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from scipy.ndimage import label, find_objects
import random
from scipy.stats import gaussian_kde
import csv

def generate_density_map_from_data(coords, map_size=(2000, 2000)):
    """
    Generates a probability density map from a set of discrete coordinates
    using Kernel Density Estimation (KDE).

    Args:
        coords (np.ndarray): An array of coordinates, shape (n, 2), where n is the number of points.
        map_size (tuple): The (width, height) of the output map.

    Returns:
        np.ndarray: A 2D array representing the probability density map.
    """
    x, y = coords[:, 0], coords[:, 1]
    
    # Create a grid for the density map
    xmin, xmax = 0, map_size[0]
    ymin, ymax = 0, map_size[1]
    X, Y = np.meshgrid(np.linspace(xmin, xmax, map_size[0]),
                       np.linspace(ymin, ymax, map_size[1]))
    
    # Use Gaussian KDE to estimate the density
    positions = np.vstack([X.ravel(), Y.ravel()])
    values = np.vstack([x, y])
    kernel = gaussian_kde(values)
    Z = np.reshape(kernel(positions).T, X.shape)
    
    # Normalize the density map to a 0-1 range
    Z = (Z - Z.min()) / (Z.max() - Z.min())
    return Z

def load_coords_from_csv(filepath):
    """
    Loads x, y coordinates from a CSV file.
    Assumes the columns are named 'x' and 'y'.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        np.ndarray: A NumPy array of (x, y) coordinates.
    """
    coords = []
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                x = float(row['x'])
                y = float(row['y'])
                coords.append([x, y])
            except (ValueError, KeyError) as e:
                print(f"Skipping row due to data error: {row}. Error: {e}")
                continue
    return np.array(coords)

def find_hotspots_with_dbscan(coords, eps=50, min_samples=5):
    """
    Identifies 'hot spots' by clustering data points using DBSCAN.

    Args:
        coords (np.ndarray): The coordinates of the data points.
        eps (float): The maximum distance between two samples for them to be considered
                     as in the same neighborhood. This is analogous to the "hot spot" radius.
        min_samples (int): The number of samples in a neighborhood for a point to be
                           considered as a core point.

    Returns:
        list: A list of NumPy arrays, where each array contains the coordinates of a
              detected hot spot cluster.
    """
    # Use DBSCAN to find clusters
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = db.labels_
    
    # Get unique cluster labels, excluding noise (label -1)
    unique_labels = set(labels)
    hotspots = []
    
    for k in unique_labels:
        if k == -1:
            # Noise points are not considered hot spots
            continue
        class_member_mask = (labels == k)
        cluster_coords = coords[class_member_mask]
        hotspots.append(cluster_coords)
        
    return hotspots

def plan_flight_path(waypoints, start_point=(0, 0)):
    """
    Generates a flight path that visits all waypoints using a greedy nearest-neighbor algorithm.

    Args:
        waypoints (np.ndarray): An array of coordinates (y, x) of waypoints.
        start_point (tuple): The starting coordinates of the flight.

    Returns:
        np.ndarray: An array of coordinates representing the planned flight path.
    """
    if len(waypoints) == 0:
        return np.array([start_point])

    flight_path = [start_point]
    unvisited = list(range(len(waypoints)))
    current_point = start_point

    while unvisited:
        distances = []
        for i in unvisited:
            # Calculate Euclidean distance from the current point to each unvisited waypoint
            dist = np.sqrt((current_point[0] - waypoints[i][0])**2 + (current_point[1] - waypoints[i][1])**2)
            distances.append((dist, i))
        
        # Find the nearest unvisited waypoint
        distances.sort()
        nearest_index = distances[0][1]
        
        # Move to the nearest waypoint and add it to the path
        next_waypoint = waypoints[nearest_index]
        flight_path.append(next_waypoint)
        
        # Update current point and remove from unvisited list
        current_point = next_waypoint
        unvisited.remove(nearest_index)
        
    return np.array(flight_path)

def visualize_flight_plan(prob_map, hotspot_clusters, flight_path, all_coords):
    """
    Visualizes the probability map, hot spots, and the generated flight path.
    
    Args:
        prob_map (np.ndarray): The 2D probability map.
        hotspot_clusters (list): A list of NumPy arrays, where each array contains
                                 the coordinates of a hot spot cluster.
        flight_path (np.ndarray): The coordinates of the planned flight path.
        all_coords (np.ndarray): All original data points.
    """
    plt.figure(figsize=(10, 8))
    plt.imshow(prob_map, cmap='hot', origin='upper')
    plt.colorbar(label='Probability')
    plt.title("Flight Plan Over Probability Map")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")

    # Plot the original data points
    plt.scatter(all_coords[:, 0], all_coords[:, 1], color='gray', s=10, alpha=0.5, label='All Data Points')

    # Plot the detected hot spot clusters
    hotspot_centroids = []
    for cluster in hotspot_clusters:
        centroid = np.mean(cluster, axis=0)
        plt.scatter(centroid[0], centroid[1], color='blue', marker='o', s=100, edgecolors='white', linewidths=1.5)
        hotspot_centroids.append(centroid)

    # Plot the flight path
    flight_path_array = np.array(flight_path)
    plt.plot(flight_path_array[:, 0], flight_path_array[:, 1], color='lime', linestyle='--', linewidth=2, marker='^', markersize=8, label='Flight Path')
    
    # Plot the start and end points
    if len(flight_path_array) > 0:
        plt.scatter(flight_path_array[0, 0], flight_path_array[0, 1], color='green', marker='s', s=150, label='Start Point', zorder=10)
        
    plt.legend()
    plt.grid(True, which='both', linestyle=':', linewidth=0.5)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Load data from the CSV file
    csv_file_path = 'bots_600.csv'
    try:
        user_data = load_coords_from_csv(csv_file_path)
        print(f"Successfully loaded {len(user_data)} points from '{csv_file_path}'.")
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found. Please make sure it's in the same directory.")
        exit()
    
    # 1. Use DBSCAN to find hot spot clusters directly from the data
    hotspot_clusters = find_hotspots_with_dbscan(user_data, eps=50, min_samples=5)
    
    if hotspot_clusters:
        # 2. Plan the flight path based on the centroids of the clusters
        hotspot_centroids = np.array([np.mean(cluster, axis=0) for cluster in hotspot_clusters])
        
        # A threshold of 0.4 is used for the visualization density map as requested (50% of 0.8)
        width, height = 2000, 2000
        prob_map = generate_density_map_from_data(user_data, map_size=(width, height))
        
        start_point = (random.uniform(0, width), random.uniform(0, height))
        flight_path = plan_flight_path(hotspot_centroids, start_point=start_point)
        
        # 3. Visualize the results
        visualize_flight_plan(prob_map, hotspot_clusters, flight_path, user_data)
        print("Flight plan generated and visualized.")
    else:
        print("No hotspots found. Try adjusting the 'eps' or 'min_samples' parameters.")
