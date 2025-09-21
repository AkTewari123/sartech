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
    print(eps)
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

def select_distributed_pois(hotspot_centroids, target_count=6, min_distance=200, map_size=(2000, 2000)):
    """
    Selects a target number of points of interest from hotspot centroids,
    ensuring they are well-distributed across the map.
    
    Args:
        hotspot_centroids (np.ndarray): Array of hotspot centroid coordinates.
        target_count (int): Target number of POIs to select (default 6).
        min_distance (float): Minimum distance between selected POIs.
        map_size (tuple): Size of the map (width, height).
    
    Returns:
        np.ndarray: Selected POIs that are well-distributed.
    """
    if len(hotspot_centroids) == 0:
        # If no hotspots, generate random POIs
        print("No hotspots found, generating random POIs")
        pois = []
        for _ in range(target_count):
            poi = (random.uniform(100, map_size[0]-100), 
                   random.uniform(100, map_size[1]-100))
            pois.append(poi)
        return np.array(pois)
    
    if len(hotspot_centroids) <= target_count:
        # If we have fewer or equal hotspots than target, use all and supplement if needed
        selected_pois = list(hotspot_centroids)
        
        # If we need more POIs, add some near existing hotspots with offset
        while len(selected_pois) < target_count:
            base_hotspot = hotspot_centroids[random.randint(0, len(hotspot_centroids)-1)]
            # Add random offset to create a new POI near the hotspot
            offset_x = random.uniform(-100, 100)
            offset_y = random.uniform(-100, 100)
            new_poi = np.array([
                np.clip(base_hotspot[0] + offset_x, 0, map_size[0]),
                np.clip(base_hotspot[1] + offset_y, 0, map_size[1])
            ])
            
            # Check if it's far enough from existing POIs
            too_close = False
            for existing_poi in selected_pois:
                if np.linalg.norm(new_poi - existing_poi) < min_distance:
                    too_close = True
                    break
            
            if not too_close:
                selected_pois.append(new_poi)
        
        return np.array(selected_pois)
    
    # If we have more hotspots than target, select the best distributed ones
    selected_pois = []
    candidates = list(hotspot_centroids)
    
    # Start with the hotspot closest to center
    center = np.array([map_size[0]/2, map_size[1]/2])
    distances_to_center = [np.linalg.norm(centroid - center) for centroid in candidates]
    first_idx = np.argmin(distances_to_center)
    selected_pois.append(candidates[first_idx])
    candidates = np.delete(candidates, first_idx, axis=0)
    
    # Select remaining POIs using maximum distance criterion
    while len(selected_pois) < target_count and len(candidates) > 0:
        max_min_distance = -1
        best_candidate_idx = -1
        
        for i, candidate in enumerate(candidates):
            # Find minimum distance to any already selected POI
            min_distance_to_selected = min([np.linalg.norm(candidate - poi) 
                                          for poi in selected_pois])
            
            # Select the candidate with the maximum minimum distance
            if min_distance_to_selected > max_min_distance:
                max_min_distance = min_distance_to_selected
                best_candidate_idx = i
        
        if best_candidate_idx >= 0:
            selected_pois.append(candidates[best_candidate_idx])
            candidates = np.delete(candidates, best_candidate_idx, axis=0)
        else:
            break
    
    # If we still need more POIs, add them strategically
    safety_counter = 0  # Add safety counter to prevent infinite loops
    max_iterations = target_count * 10  # Maximum iterations allowed
    
    while len(selected_pois) < target_count and safety_counter < max_iterations:
        safety_counter += 1
        
        # Find the largest gap between existing POIs and place a new one there
        best_position = None
        max_min_distance = 0
        
        # Try multiple random positions and pick the one farthest from existing POIs
        for _ in range(50):  # Try 50 random positions
            candidate = np.array([
                random.uniform(100, map_size[0]-100),
                random.uniform(100, map_size[1]-100)
            ])
            
            min_distance_to_existing = min([np.linalg.norm(candidate - poi) 
                                          for poi in selected_pois])
            
            if min_distance_to_existing > max_min_distance:
                max_min_distance = min_distance_to_existing
                best_position = candidate
        
        # Dynamically reduce min_distance requirement if having trouble placing POIs
        dynamic_min_distance = min_distance * (1.0 - safety_counter / max_iterations)
        
        if best_position is not None and max_min_distance >= dynamic_min_distance:
            selected_pois.append(best_position)
        else:
            # If we can't find a good position, place it randomly but ensure minimum distance
            attempts = 0
            while attempts < 50 and len(selected_pois) < target_count:  # Reduce attempts
                candidate = np.array([
                    random.uniform(100, map_size[0]-100),
                    random.uniform(100, map_size[1]-100)
                ])
                
                min_distance_to_existing = min([np.linalg.norm(candidate - poi) 
                                              for poi in selected_pois])
                
                if min_distance_to_existing >= dynamic_min_distance * 0.5:  # Further relax constraint
                    selected_pois.append(candidate)
                    break
                attempts += 1
            
            if attempts >= 50:
                # If still can't place with constraints, just add it anyway to avoid infinite loop
                candidate = np.array([
                    random.uniform(100, map_size[0]-100),
                    random.uniform(100, map_size[1]-100)
                ])
                selected_pois.append(candidate)
    
    print(f"Selected {len(selected_pois)} POIs after {safety_counter} iterations")
    return np.array(selected_pois)

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

def select_top_dense_grid_pois(coords, grid_rows=5, grid_cols=5, top_k=10):
    """
    Splits the coordinate space into a grid (grid_rows x grid_cols), counts points per cell,
    selects the top_k densest cells, and returns the centers of those cells ordered by density desc.

    Args:
        coords (np.ndarray): Array of (x, y) coordinates.
        grid_rows (int): Number of grid rows (default 5).
        grid_cols (int): Number of grid cols (default 5).
        top_k (int): Number of densest cells to return (default 10).

    Returns:
        tuple[np.ndarray, list[dict], np.ndarray, np.ndarray]:
            - centers (np.ndarray): (k,2) centers of selected cells ordered by density desc.
            - cells_info (list[dict]): Per-cell metadata with indices and counts.
            - xedges (np.ndarray): Bin edges along x (length grid_cols+1).
            - yedges (np.ndarray): Bin edges along y (length grid_rows+1).
    """
    if coords is None or len(coords) == 0:
        return np.empty((0, 2)), [], np.array([]), np.array([])

    x = coords[:, 0]
    y = coords[:, 1]

    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))

    # Handle degenerate ranges by adding a small buffer
    if x_max - x_min < 1e-6:
        x_max = x_min + 1.0
    if y_max - y_min < 1e-6:
        y_max = y_min + 1.0

    xedges = np.linspace(x_min, x_max, grid_cols + 1)
    yedges = np.linspace(y_min, y_max, grid_rows + 1)

    # Note: histogram2d expects x first then y
    H, xedges_out, yedges_out = np.histogram2d(x, y, bins=[xedges, yedges])
    # Use the returned edges to be precise
    xedges = xedges_out
    yedges = yedges_out

    # Flatten and get top_k indices by count descending
    flat = H.ravel()
    # If fewer cells than top_k, adjust
    k = min(top_k, flat.size)
    if k == 0:
        return np.empty((0, 2)), [], xedges, yedges

    # argsort descending
    top_indices = np.argsort(flat)[::-1][:k]

    centers = []
    cells_info = []
    n_x_bins = len(xedges) - 1
    n_y_bins = len(yedges) - 1
    for idx in top_indices:
        # Map flat index to (ix, iy)
        ix = idx // n_y_bins
        iy = idx % n_y_bins
        cx = 0.5 * (xedges[ix] + xedges[ix + 1])
        cy = 0.5 * (yedges[iy] + yedges[iy + 1])
        centers.append([cx, cy])
        cells_info.append({
            'ix': int(ix),
            'iy': int(iy),
            'count': int(H[ix, iy])
        })

    centers = np.array(centers)
    return centers, cells_info, xedges, yedges

def plan_flight_path_in_order(waypoints_ordered, start_point=(0, 0)):
    """
    Simple path that visits waypoints in the given order (no reordering),
    starting from start_point.

    Args:
        waypoints_ordered (np.ndarray): (n,2) waypoints in desired visit order.
        start_point (tuple): starting coordinate.

    Returns:
        np.ndarray: path including start followed by waypoints.
    """
    if waypoints_ordered is None or len(waypoints_ordered) == 0:
        return np.array([start_point])
    path = [start_point]
    path.extend(list(waypoints_ordered))
    return np.array(path)

def visualize_flight_plan(prob_map, hotspot_clusters, flight_path, all_coords, selected_pois):
    """
    Visualizes the probability map, hot spots, and the generated flight path.
    
    Args:
        prob_map (np.ndarray): The 2D probability map.
        hotspot_clusters (list): A list of NumPy arrays, where each array contains
                                 the coordinates of a hot spot cluster.
        flight_path (np.ndarray): The coordinates of the planned flight path.
        all_coords (np.ndarray): All original data points.
        selected_pois (np.ndarray): The selected points of interest.
    """
    plt.figure(figsize=(12, 10))
    plt.imshow(prob_map, cmap='hot', origin='upper')
    plt.colorbar(label='Probability Density')
    plt.title("Flight Plan Over Probability Map with Distributed POIs")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")

    # Plot the original data points
    plt.scatter(all_coords[:, 0], all_coords[:, 1], color='lightgray', s=5, alpha=0.3, label='All Data Points')

    # Plot the detected hot spot clusters
    colors = plt.cm.Set3(np.linspace(0, 1, len(hotspot_clusters)))
    for i, cluster in enumerate(hotspot_clusters):
        centroid = np.mean(cluster, axis=0)
        plt.scatter(cluster[:, 0], cluster[:, 1], color=colors[i], s=15, alpha=0.6, label=f'Hotspot {i+1}')
        plt.scatter(centroid[0], centroid[1], color='darkblue', marker='x', s=100, linewidths=2)

    # Plot the selected POIs
    plt.scatter(selected_pois[:, 0], selected_pois[:, 1], color='red', marker='o', s=150, 
                edgecolors='white', linewidths=2, label='Selected POIs', zorder=8)

    # Plot the flight path
    flight_path_array = np.array(flight_path)
    plt.plot(flight_path_array[:, 0], flight_path_array[:, 1], color='lime', linestyle='--', 
             linewidth=3, marker='^', markersize=10, label='Flight Path', zorder=9)
    
    # Plot the start point
    if len(flight_path_array) > 0:
        plt.scatter(flight_path_array[0, 0], flight_path_array[0, 1], color='green', 
                   marker='s', s=200, label='Start Point', zorder=10, edgecolors='white', linewidths=2)
    
    # Add distance annotations between POIs
    for i in range(len(selected_pois)):
        for j in range(i+1, len(selected_pois)):
            distance = np.linalg.norm(selected_pois[i] - selected_pois[j])
            mid_point = (selected_pois[i] + selected_pois[j]) / 2
            plt.text(mid_point[0], mid_point[1], f'{distance:.0f}', fontsize=8, 
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
        
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, which='both', linestyle=':', linewidth=0.5, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print(f"\nFlight Plan Summary:")
    print(f"Number of POIs: {len(selected_pois)}")
    print(f"Total flight path points: {len(flight_path_array)}")
    
    if len(selected_pois) > 1:
        distances = []
        for i in range(len(selected_pois)):
            for j in range(i+1, len(selected_pois)):
                distance = np.linalg.norm(selected_pois[i] - selected_pois[j])
                distances.append(distance)
        
        print(f"Min distance between POIs: {min(distances):.1f}")
        print(f"Max distance between POIs: {max(distances):.1f}")
        print(f"Average distance between POIs: {np.mean(distances):.1f}")

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
    hotspot_clusters = find_hotspots_with_dbscan(user_data, eps=5, min_samples=5)
    
    # 2. Get hotspot centroids and select distributed POIs
    if hotspot_clusters:
        hotspot_centroids = np.array([np.mean(cluster, axis=0) for cluster in hotspot_clusters])
    else:
        hotspot_centroids = np.array([])
    
    # Select 6-7 well-distributed POIs (randomly choose between 6 and 7)
    target_poi_count = random.choice([6, 7])
    selected_pois = select_distributed_pois(hotspot_centroids, target_count=target_poi_count, min_distance=250)
    
    print(f"Selected {len(selected_pois)} POIs for the flight plan.")
    
    # 3. Generate probability map and plan flight path
    width, height = 2000, 2000
    prob_map = generate_density_map_from_data(user_data, map_size=(width, height))
    
    start_point = (random.uniform(100, width-100), random.uniform(100, height-100))
    flight_path = plan_flight_path(selected_pois, start_point=start_point)
    
    # 4. Visualize the results
    visualize_flight_plan(prob_map, hotspot_clusters, flight_path, user_data, selected_pois)
    print("Flight plan generated and visualized with distributed POIs.")