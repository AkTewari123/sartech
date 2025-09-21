"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export default function SearchArea() {
  const searchParams = useSearchParams();
  const [mapInstance, setMapInstance] = useState<any | null>(null);
  const [boundingBox, setBoundingBox] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [animatedLayers, setAnimatedLayers] = useState<{ [key: string]: any }>(
    {}
  );
  const [animationActive, setAnimationActive] = useState(false);
  const [animationProgress, setAnimationProgress] = useState(0);
  const [currentAnimationStep, setCurrentAnimationStep] = useState(0);
  const [maskOverlay, setMaskOverlay] = useState<any>(null);
  const [originalMapView, setOriginalMapView] = useState<{
    center: { lat: number; lng: number };
    zoom: number;
  } | null>(null);
  const [isZoomedIn, setIsZoomedIn] = useState(false);

  // New workflow state
  const [workflowStep, setWorkflowStep] = useState<
    "segmentation" | "heatmap" | "flightpath" | "complete"
  >("segmentation");
  const [heatmapData, setHeatmapData] = useState<any>(null);
  const [heatmapOverlay, setHeatmapOverlay] = useState<any>(null);
  const [flightPathData, setFlightPathData] = useState<any>(null);
  const [flightPathOverlay, setFlightPathOverlay] = useState<any>(null);
  const [currentView, setCurrentView] = useState<"segmentation" | "heatmap" | "flightpath">(
    "segmentation"
  );
  const [terrainAnalysisComplete, setTerrainAnalysisComplete] = useState(false);
  const [heatmapComplete, setHeatmapComplete] = useState(false);

  const animationRef = useRef<{ active: boolean; timeouts: NodeJS.Timeout[] }>({
    active: false,
    timeouts: [],
  });
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

  // Parse URL parameters and set bounding box
  useEffect(() => {
    const north = searchParams.get("north");
    const south = searchParams.get("south");
    const east = searchParams.get("east");
    const west = searchParams.get("west");
    const centerLat = searchParams.get("lat");
    const centerLng = searchParams.get("lng");

    let bbox;

    if (centerLat && centerLng) {
      // Create 10km x 10km square around center point
      const lat = parseFloat(centerLat);
      const lng = parseFloat(centerLng);

      // Approximate conversion: 1 degree lat ≈ 111km, 1 degree lng ≈ 111km * cos(lat)
      const latOffset = 10 / (2 * 111); // 5km in each direction
      const lngOffset = 10 / (2 * 111 * Math.cos((lat * Math.PI) / 180)); // 5km in each direction, adjusted for latitude

      bbox = {
        north: lat + latOffset,
        south: lat - latOffset,
        east: lng + lngOffset,
        west: lng - lngOffset,
      };

      console.log(
        "Creating 10km x 10km square around center point:",
        { centerLat: lat, centerLng: lng },
        bbox
      );
      setBoundingBox(bbox);
    } else if (north && south && east && west) {
      // Use explicit bounding box coordinates
      bbox = {
        north: parseFloat(north),
        south: parseFloat(south),
        east: parseFloat(east),
        west: parseFloat(west),
      };

      console.log("Setting bounding box from URL parameters:", bbox);
      setBoundingBox(bbox);
    } else {
      // Default to Princeton area if no parameters
      const defaultBbox = {
        north: 40.3622,
        south: 40.3158,
        east: -74.6252,
        west: -74.6958,
      };
      console.log("Using default Princeton bounding box:", defaultBbox);
      setBoundingBox(defaultBbox);
    }
  }, [searchParams]);

  // Dark Apple-like style for map (same as maps page)
  const darkAppleStyle = [
    {
      featureType: "all",
      elementType: "labels",
      stylers: [
        {
          visibility: "off",
        },
      ],
    },
    {
      featureType: "all",
      elementType: "labels.text",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "all",
      elementType: "labels.text.fill",
      stylers: [
        {
          weight: 7.5,
        },
        {
          color: "#708090",
        },
      ],
    },
    {
      featureType: "all",
      elementType: "labels.text.stroke",
      stylers: [
        {
          weight: 1.1,
        },
        {
          color: "#3c6382",
        },
      ],
    },
    {
      featureType: "all",
      elementType: "labels.icon",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "administrative",
      elementType: "all",
      stylers: [
        {
          visibility: "off",
        },
      ],
    },
    {
      featureType: "administrative.country",
      elementType: "labels.text.fill",
      stylers: [
        {
          saturation: "41",
        },
        {
          lightness: "20",
        },
      ],
    },
    {
      featureType: "administrative.locality",
      elementType: "labels",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "administrative.locality",
      elementType: "labels.text",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "landscape",
      elementType: "all",
      stylers: [
        {
          color: "#1e272e",
        },
      ],
    },
    {
      featureType: "poi",
      elementType: "all",
      stylers: [
        {
          visibility: "off",
        },
      ],
    },
    {
      featureType: "road",
      elementType: "geometry.fill",
      stylers: [
        {
          color: "#708090",
        },
        {
          weight: 0.5,
        },
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "road",
      elementType: "geometry.stroke",
      stylers: [
        {
          color: "#273c75",
        },
        {
          weight: 1.4,
        },
      ],
    },
    {
      featureType: "road",
      elementType: "labels",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "road",
      elementType: "labels.text",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "road",
      elementType: "labels.icon",
      stylers: [
        {
          visibility: "off",
        },
        {
          saturation: "-100",
        },
        {
          lightness: "0",
        },
        {
          gamma: "0.00",
        },
        {
          weight: "1",
        },
      ],
    },
    {
      featureType: "road.arterial",
      elementType: "all",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "road.arterial",
      elementType: "labels.text",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "road.local",
      elementType: "geometry.fill",
      stylers: [
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "transit",
      elementType: "all",
      stylers: [
        {
          visibility: "off",
        },
      ],
    },
    {
      featureType: "water",
      elementType: "all",
      stylers: [
        {
          color: "#778899",
        },
        {
          visibility: "on",
        },
      ],
    },
    {
      featureType: "water",
      elementType: "geometry.fill",
      stylers: [
        {
          visibility: "on",
        },
        {
          saturation: "100",
        },
        {
          gamma: "1.00",
        },
        {
          lightness: "54",
        },
      ],
    },
    {
      featureType: "water",
      elementType: "geometry.stroke",
      stylers: [
        {
          visibility: "off",
        },
      ],
    },
  ];

  // Generate animated layers from API
  const generateAnimatedLayers = async () => {
    if (!boundingBox) return;

    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/segmentation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(boundingBox),
      });

      if (response.ok) {
        const data = await response.json();
        const layers = data.layers;

        // Clear existing overlays
        Object.values(animatedLayers).forEach((overlay: any) => {
          if (overlay) overlay.setMap(null);
        });
        setAnimatedLayers({});

        // Create overlays for each layer
        const newLayers: { [key: string]: any } = {};

        for (const [layerName, base64Data] of Object.entries(layers)) {
          const imageUrl = `data:image/png;base64,${base64Data}`;

          const overlay = new window.google.maps.GroundOverlay(
            imageUrl,
            {
              north: boundingBox.north,
              south: boundingBox.south,
              east: boundingBox.east,
              west: boundingBox.west,
            },
            {
              opacity: 0,
            }
          );

          overlay.setMap(mapInstance);
          newLayers[layerName] = overlay;
        }

        setAnimatedLayers(newLayers);

        // Create dark mask overlay for contrast
        createMaskOverlay();

        // Smooth zoom to the area of interest
        setTimeout(() => {
          zoomToBoundingBox();
        }, 500);

        // Mark that segmentation layers are ready
        console.log("All layers loaded successfully");
      } else {
        console.error("Failed to generate animated layers");
      }
    } catch (error) {
      console.error("Error generating animated layers:", error);
    } finally {
      setLoading(false);
    }
  };

  // Start animation sequence
  const startAnimation = () => {
    const layerOrder = ["water", "sparse_forest", "dense_forest", "roads"];
    const availableLayers = layerOrder.filter((layer) => animatedLayers[layer]);

    if (availableLayers.length === 0) {
      console.log("No layers available for animation");
      return;
    }

    console.log("Starting animation with layers:", availableLayers);

    // Clear any existing timeouts
    animationRef.current.timeouts.forEach((timeout) => clearTimeout(timeout));
    animationRef.current.timeouts = [];

    setAnimationActive(true);
    setCurrentAnimationStep(0);
    setAnimationProgress(0);
    animationRef.current.active = true;

    // Hide all layers first
    availableLayers.forEach((layerName) => {
      const overlay = animatedLayers[layerName];
      if (overlay) {
        overlay.setOpacity(0);
      }
    });

    // Smooth animation with fade-in effect
    let currentStep = 0;

    const animateNextLayer = () => {
      if (
        !animationRef.current.active ||
        currentStep >= availableLayers.length
      ) {
        // Animation complete or stopped
        if (animationRef.current.active) {
          console.log("Animation cycle complete - starting heatmap generation");
          setAnimationActive(false);
          animationRef.current.active = false;

          // Animation complete - terrain analysis done
          setTerrainAnalysisComplete(true);
        }
        return;
      }

      const layerName = availableLayers[currentStep];
      const overlay = animatedLayers[layerName];

      if (overlay) {
        console.log(
          `Animating layer: ${layerName} (step ${currentStep + 1}/${
            availableLayers.length
          })`
        );
        setCurrentAnimationStep(currentStep + 1);
        setAnimationProgress(((currentStep + 1) / availableLayers.length) * 100);

        // Smooth fade-in animation
        let opacity = 0;
        const targetOpacity = 0.85;
        const fadeStep = 0.03;
        const fadeInterval = 30; // ms between steps

        const fadeIn = () => {
          if (!animationRef.current.active) return;

          opacity += fadeStep;
          const currentOpacity = Math.min(opacity, targetOpacity);
          overlay.setOpacity(currentOpacity);

          if (opacity >= targetOpacity) {
            // Fade complete, schedule next layer
            currentStep++;
            const nextTimeout = setTimeout(animateNextLayer, 1000); // Fixed 1 second delay
            animationRef.current.timeouts.push(nextTimeout);
          } else {
            // Continue fading
            const fadeTimeout = setTimeout(fadeIn, fadeInterval);
            animationRef.current.timeouts.push(fadeTimeout);
          }
        };

        fadeIn();
      } else {
        console.log(`Layer ${layerName} not found, skipping`);
        currentStep++;
        const skipTimeout = setTimeout(animateNextLayer, 100);
        animationRef.current.timeouts.push(skipTimeout);
      }
    };

    // Start animation after short delay
    const startTimeout = setTimeout(animateNextLayer, 500);
    animationRef.current.timeouts.push(startTimeout);
  };

  // Stop animation
  const stopAnimation = () => {
    console.log("Stopping animation");

    // Clear all timeouts
    animationRef.current.timeouts.forEach((timeout) => clearTimeout(timeout));
    animationRef.current.timeouts = [];
    animationRef.current.active = false;

    setAnimationActive(false);
    setCurrentAnimationStep(0);

    // Show all layers at full opacity
    Object.entries(animatedLayers).forEach(([layerName, overlay]) => {
      if (overlay) {
        console.log(`Setting ${layerName} to full opacity`);
        overlay.setOpacity(0.7);
      }
    });
  };

  // Clear all layers
  const clearAllLayers = () => {
    // Stop animation first
    animationRef.current.timeouts.forEach((timeout) => clearTimeout(timeout));
    animationRef.current.timeouts = [];
    animationRef.current.active = false;

    setAnimationActive(false);
    setCurrentAnimationStep(0);

    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(null);
    });
    setAnimatedLayers({});

    // Remove mask overlay
    if (maskOverlay) {
      if (Array.isArray(maskOverlay)) {
        maskOverlay.forEach((overlay) => overlay.setMap(null));
      } else {
        maskOverlay.setMap(null);
      }
      setMaskOverlay(null);
    }
  };

  // Create dark mask overlay outside bounding box
  const createMaskOverlay = () => {
    if (!boundingBox || !mapInstance) {
      console.log("Cannot create mask: missing boundingBox or mapInstance", {
        boundingBox,
        mapInstance,
      });
      return;
    }

    console.log("Creating mask overlay for bounding box:", boundingBox);

    // Remove existing mask
    if (maskOverlay) {
      if (Array.isArray(maskOverlay)) {
        maskOverlay.forEach((overlay) => overlay.setMap(null));
      } else {
        maskOverlay.setMap(null);
      }
    }

    try {
      // Create 4 rectangles around the bounding box
      const mapBounds = mapInstance.getBounds();
      if (!mapBounds) {
        console.log("Could not get map bounds");
        return;
      }

      const ne = mapBounds.getNorthEast();
      const sw = mapBounds.getSouthWest();

      const maskRectangles = [];

      // Top rectangle
      const topRect = new window.google.maps.Rectangle({
        bounds: {
          north: ne.lat(),
          south: boundingBox.north,
          east: ne.lng(),
          west: sw.lng(),
        },
        fillColor: "#000000",
        fillOpacity: 0.5,
        strokeWeight: 0,
        clickable: false,
        zIndex: 1000,
      });
      topRect.setMap(mapInstance);
      maskRectangles.push(topRect);

      // Bottom rectangle
      const bottomRect = new window.google.maps.Rectangle({
        bounds: {
          north: boundingBox.south,
          south: sw.lat(),
          east: ne.lng(),
          west: sw.lng(),
        },
        fillColor: "#000000",
        fillOpacity: 0.5,
        strokeWeight: 0,
        clickable: false,
        zIndex: 1000,
      });
      bottomRect.setMap(mapInstance);
      maskRectangles.push(bottomRect);

      // Left rectangle
      const leftRect = new window.google.maps.Rectangle({
        bounds: {
          north: boundingBox.north,
          south: boundingBox.south,
          east: boundingBox.west,
          west: sw.lng(),
        },
        fillColor: "#000000",
        fillOpacity: 0.5,
        strokeWeight: 0,
        clickable: false,
        zIndex: 1000,
      });
      leftRect.setMap(mapInstance);
      maskRectangles.push(leftRect);

      // Right rectangle
      const rightRect = new window.google.maps.Rectangle({
        bounds: {
          north: boundingBox.north,
          south: boundingBox.south,
          east: ne.lng(),
          west: boundingBox.east,
        },
        fillColor: "#000000",
        fillOpacity: 0.5,
        strokeWeight: 0,
        clickable: false,
        zIndex: 1000,
      });
      rightRect.setMap(mapInstance);
      maskRectangles.push(rightRect);

      setMaskOverlay(maskRectangles);
      console.log(
        "Mask overlay created successfully with",
        maskRectangles.length,
        "rectangles"
      );
    } catch (error) {
      console.error("Error creating mask overlay:", error);
    }
  };

  // Smooth zoom to bounding box area
  const layerOrder = ["water", "sparse_forest", "dense_forest", "roads"];

  // Calculate area of bounding box in km²
  const calculateArea = (bounds: BoundingBox) => {
    const R = 6371; // Earth's radius in km
    const lat1 = (bounds.north * Math.PI) / 180;
    const lat2 = (bounds.south * Math.PI) / 180;
    const deltaLat = ((bounds.south - bounds.north) * Math.PI) / 180;
    const deltaLon = ((bounds.east - bounds.west) * Math.PI) / 180;

    const a =
      Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
      Math.cos(lat1) *
        Math.cos(lat2) *
        Math.sin(deltaLon / 2) *
        Math.sin(deltaLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c * Math.abs((bounds.east - bounds.west) / 360) * 40075;
  };

  const zoomToBoundingBox = () => {
    if (!boundingBox || !mapInstance) {
      console.log("Cannot zoom: missing boundingBox or mapInstance");
      return;
    }

    // Save current map view before zooming
    if (!originalMapView && !isZoomedIn) {
      setOriginalMapView({
        center: {
          lat: mapInstance.getCenter().lat(),
          lng: mapInstance.getCenter().lng(),
        },
        zoom: mapInstance.getZoom(),
      });
    }

    // Calculate bounds and optimal zoom level
    const bounds = new window.google.maps.LatLngBounds(
      new window.google.maps.LatLng(boundingBox.south, boundingBox.west),
      new window.google.maps.LatLng(boundingBox.north, boundingBox.east)
    );

    // Add some padding around the bounding box
    const padding = {
      top: 50,
      right: 50,
      bottom: 50,
      left: 50,
    };

    console.log("Zooming to bounding box with smooth animation");

    // Smooth zoom animation
    mapInstance.fitBounds(bounds, padding);

    // Use panToBounds for smoother animation
    mapInstance.panToBounds(bounds, padding);

    setIsZoomedIn(true);
  };

  // Zoom back to original view
  const zoomToOriginalView = () => {
    if (!mapInstance || !originalMapView) {
      console.log("Cannot zoom back: missing mapInstance or originalMapView");
      return;
    }

    console.log("Zooming back to original view");

    // Smooth animation back to original position
    mapInstance.panTo(originalMapView.center);
    mapInstance.setZoom(originalMapView.zoom);

    setIsZoomedIn(false);
  };

  // Reset to default Princeton view
  const resetToDefaultView = () => {
    if (!mapInstance) return;

    console.log("Resetting to default Princeton view");

    const defaultCenter = { lat: 40.34, lng: -74.66 };
    const defaultZoom = 13;

    mapInstance.panTo(defaultCenter);
    mapInstance.setZoom(defaultZoom);

    setOriginalMapView(null);
    setIsZoomedIn(false);
  };

  // Generate heatmap and flight plan after segmentation
  const generateHeatmapAndFlightPlan = async () => {
    if (!boundingBox) {
      console.error("No bounding box available for heatmap generation");
      return;
    }

    setWorkflowStep("heatmap");
    setLoading(true);

    try {
      console.log("Generating heatmap...");

      // Call the unified workflow API
      const response = await fetch("http://localhost:8000/workflow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          bbox: boundingBox,
          generate_heatmap: true,
          generate_flightplan: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Workflow data received:", data);

      setHeatmapData(data.heatmap_data);

      // Display heatmap
      if (data.heatmap_data) {
        await displayHeatmap(data.heatmap_data);
        setCurrentView("heatmap"); // Switch to heatmap view after generation
        setHeatmapComplete(true);
        setWorkflowStep("heatmap"); // Stay in heatmap step, not complete yet
      }
    } catch (error) {
      console.error("Error generating heatmap:", error);
      setWorkflowStep("segmentation"); // Reset on error
    } finally {
      setLoading(false);
    }
  };

  // Generate flight path after heatmap
  const generateFlightPath = async () => {
    if (!boundingBox || !heatmapData) {
      console.error("No bounding box or heatmap data available for flight path generation");
      return;
    }

    setWorkflowStep("flightpath");
    setLoading(true);

    try {
      console.log("Generating flight path with heatmap coordinates:", heatmapData.coordinates?.length);

      // Format coordinates for the API (ensure they have x, y structure)
      const formattedCoordinates = heatmapData.coordinates.map((coord: any) => ({
        x: coord.x || coord.lng || coord.longitude,
        y: coord.y || coord.lat || coord.latitude
      }));

      console.log("Formatted coordinates sample:", formattedCoordinates.slice(0, 3));

      // Call the direct flightplan endpoint with existing heatmap coordinates
      const response = await fetch("http://localhost:8000/flightplan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formattedCoordinates),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Flight plan API error:", response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const flightPlanData = await response.json();
      console.log("Flight path data received:", flightPlanData);
      console.log("Flight path waypoints:", flightPlanData.flight_path?.length || 0);
      console.log("Hotspots found:", flightPlanData.num_hotspots || 0);

      setFlightPathData(flightPlanData);

      // Display flight path - use flight_path instead of waypoints
      if (flightPlanData && flightPlanData.flight_path && flightPlanData.flight_path.length > 0) {
        await displayFlightPath(flightPlanData);
        setCurrentView("flightpath"); // Switch to flight path view after generation
        setWorkflowStep("complete");
      } else {
        console.error("No flight path in response data:", flightPlanData);
        alert("Flight path generation failed: No flight path generated. Check if heatmap has enough data points.");
      }
    } catch (error) {
      console.error("Error generating flight path:", error);
      setWorkflowStep("heatmap"); // Reset to heatmap step on error
    } finally {
      setLoading(false);
    }
  };

  const displayHeatmap = async (heatmapData: any) => {
    if (!mapInstance || !heatmapData?.coordinates) return;

    console.log(
      "Displaying heatmap with",
      heatmapData.coordinates.length,
      "points"
    );

    // Clear existing heatmap
    if (heatmapOverlay) {
      heatmapOverlay.setMap(null);
    }

    // FIXED: Ensure coordinates are properly interpreted
    const heatmapPoints = heatmapData.coordinates.map((coord: any) => {
      // Make sure we're using the correct coordinate order: lat, lng
      const lat = coord.y || coord.lat;
      const lng = coord.x || coord.lng;
      
      // Validate coordinates are within expected bounds
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        console.warn("Invalid coordinates detected:", { lat, lng });
        return null;
      }
      
      return {
        location: new window.google.maps.LatLng(lat, lng),
        weight: coord.intensity || 1,
      };
    }).filter(point => point !== null); // Remove invalid points

    console.log("Processed heatmap points:", heatmapPoints.length);
    console.log("Sample coordinates:", heatmapPoints.slice(0, 3));

    const heatmap = new window.google.maps.visualization.HeatmapLayer({
      data: heatmapPoints,
      map: mapInstance,
      radius: 20,
      opacity: 0.8,
      dissipating: true, // IMPORTANT: This prevents the heatmap from changing on zoom
      gradient: [
        "rgba(255, 255, 255, 0)", // Transparent white (no data)
        "rgba(255, 255, 255, 0.1)", // Very faint white
        "rgba(255, 255, 255, 0.3)", // Light white
        "rgba(255, 255, 224, 0.5)", // Very light yellow
        "rgba(255, 255, 150, 0.7)", // Light yellow
        "rgba(255, 255, 0, 0.8)", // Yellow
        "rgba(255, 215, 0, 0.85)", // Gold
        "rgba(255, 165, 0, 0.9)", // Orange
        "rgba(255, 140, 0, 0.95)", // Dark orange
        "rgba(255, 69, 0, 1)", // Red-orange
        "rgba(255, 0, 0, 1)", // Red (highest probability)
      ],
    });

    setHeatmapOverlay(heatmap);
  };


  const displayFlightPath = async (flightPlanData: any) => {
    if (!mapInstance || !flightPlanData?.flight_path) return;

    console.log(
      "Displaying flight path with",
      flightPlanData.flight_path.length,
      "waypoints"
    );

    // Clear existing flight path
    if (flightPathOverlay) {
      if (Array.isArray(flightPathOverlay)) {
        flightPathOverlay.forEach((overlay) => overlay.setMap(null));
      } else {
        flightPathOverlay.setMap(null);
      }
    }

    const overlays = [];

    // FIXED: Ensure consistent coordinate interpretation
    const pathCoordinates = flightPlanData.flight_path.map((waypoint: any) => {
      const lat = waypoint.y || waypoint.lat;
      const lng = waypoint.x || waypoint.lng || waypoint.lon;
      
      // Validate coordinates
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        console.warn("Invalid flight path coordinates:", { lat, lng });
        return null;
      }
      
      return { lat, lng };
    }).filter(coord => coord !== null);

    console.log("Flight path coordinates:", pathCoordinates);

    if (pathCoordinates.length === 0) {
      console.error("No valid flight path coordinates");
      return;
    }

    const flightPath = new window.google.maps.Polyline({
      path: pathCoordinates,
      geodesic: true,
      strokeColor: "#FF0000",
      strokeOpacity: 1.0,
      strokeWeight: 3,
    });

    flightPath.setMap(mapInstance);
    overlays.push(flightPath);

    // Add waypoint markers
    pathCoordinates.forEach((coord, index) => {
      const marker = new window.google.maps.Marker({
        position: coord,
        map: mapInstance,
        title: `Waypoint ${index + 1}`,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          fillColor: index === 0 ? "#00FF00" : index === pathCoordinates.length - 1 ? "#FF0000" : "#0000FF",
          fillOpacity: 0.8,
          strokeColor: "#FFFFFF",
          strokeWeight: 2,
          scale: 8,
        },
      });
      overlays.push(marker);
    });

    setFlightPathOverlay(overlays);
  };

  const switchToSegmentationView = () => {
    if (heatmapOverlay) {
      heatmapOverlay.setMap(null);
    }

    // Show segmentation layers
    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(mapInstance);
    });

    setCurrentView("segmentation");
  };

  const switchToHeatmapView = () => {
    // Hide segmentation layers
    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(null);
    });

    // Show heatmap
    if (heatmapOverlay && mapInstance) {
      heatmapOverlay.setMap(mapInstance);
    }

    setCurrentView("heatmap");
  };

  const switchToFlightPathView = () => {
    // Hide segmentation layers
    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(null);
    });

    // Hide heatmap
    if (heatmapOverlay) {
      heatmapOverlay.setMap(null);
    }

    // Show flight path
    if (flightPathOverlay && mapInstance) {
      if (Array.isArray(flightPathOverlay)) {
        flightPathOverlay.forEach((overlay) => overlay.setMap(mapInstance));
      } else {
        flightPathOverlay.setMap(mapInstance);
      }
    }

    setCurrentView("flightpath");
  };

  // Update existing switch functions to handle flight path
  const switchToSegmentationViewUpdated = () => {
    if (heatmapOverlay) {
      heatmapOverlay.setMap(null);
    }
    if (flightPathOverlay) {
      if (Array.isArray(flightPathOverlay)) {
        flightPathOverlay.forEach((overlay) => overlay.setMap(null));
      } else {
        flightPathOverlay.setMap(null);
      }
    }

    // Show segmentation layers
    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(mapInstance);
    });

    setCurrentView("segmentation");
  };

  const switchToHeatmapViewUpdated = () => {
    // Hide segmentation layers
    Object.values(animatedLayers).forEach((overlay: any) => {
      if (overlay) overlay.setMap(null);
    });

    // Hide flight path
    if (flightPathOverlay) {
      if (Array.isArray(flightPathOverlay)) {
        flightPathOverlay.forEach((overlay) => overlay.setMap(null));
      } else {
        flightPathOverlay.setMap(null);
      }
    }

    // Show heatmap
    if (heatmapOverlay && mapInstance) {
      heatmapOverlay.setMap(mapInstance);
    }

    setCurrentView("heatmap");
  };

  // Initialize Google Map
  useEffect(() => {
    if (!apiKey) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("search-map") as HTMLElement,
        {
          center: { lat: 40.34, lng: -74.66 }, // Princeton area
          zoom: 13,
          mapTypeId: "satellite",
          styles: null,
          tilt: 0,
          disableDefaultUI: true, // <-- disables all default UI controls
          clickableIcons: false, // optional: disables POI icons
          gestureHandling: "greedy", // optional: improves map interaction
        }
      );

      setMapInstance(map);
    };

    // Load Google Maps script
    if (!document.getElementById("google-maps-search-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-search-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=visualization&callback=initSearchMap`;
      script.async = true;
      script.defer = true;
      // @ts-ignore
      window.initSearchMap = initMap;
      document.body.appendChild(script);
    } else {
      // @ts-ignore
      if (window.google && window.google.maps) {
        initMap();
      }
    }
  }, [apiKey]);

  // Animation state effect - cleanup when component unmounts or animation stops
  useEffect(() => {
    return () => {
      // Cleanup animation when component unmounts
      animationRef.current.timeouts.forEach((timeout) => clearTimeout(timeout));
      animationRef.current.timeouts = [];
      animationRef.current.active = false;
      setAnimationActive(false);
    };
  }, []);

  // Effect to handle animation state changes
  useEffect(() => {
    if (!animationActive) {
      animationRef.current.active = false;
      setCurrentAnimationStep(0);
    }
  }, [animationActive]);

  // Auto-start animation when map and bounding box are ready
  useEffect(() => {
    if (
      mapInstance &&
      boundingBox &&
      !loading &&
      Object.keys(animatedLayers).length === 0
    ) {
      console.log("Auto-starting segmentation analysis...");
      // Small delay to ensure map is fully loaded
      setTimeout(() => {
        generateAnimatedLayers();
      }, 1000);
    }
  }, [mapInstance, boundingBox]);

  // Auto-start animation sequence when layers are ready (only once)
  const [hasAutoStarted, setHasAutoStarted] = useState(false);
  useEffect(() => {
    if (
      Object.keys(animatedLayers).length > 0 &&
      !animationActive &&
      !hasAutoStarted
    ) {
      console.log("Auto-starting animation sequence...");
      setHasAutoStarted(true);
      // Small delay to ensure layers are fully rendered
      setTimeout(() => {
        startAnimation();
      }, 1500);
    }
  }, [animatedLayers, hasAutoStarted]);

  return (
    <div className="relative w-full h-screen m-0 p-0">
      <div id="search-map" style={{ width: "100%", height: "100%" }} />

      {/* Simplified Control Panel */}
      <div className="absolute top-1/2 left-8 transform -translate-y-1/2 bg-white min-w-[300px] p-4 rounded-lg shadow-lg z-10 max-w-sm">
        <h2 className="text-lg font-semibold mb-4 text-center">
          {!terrainAnalysisComplete &&
            workflowStep === "segmentation" &&
            "Terrain Analysis"}
          {terrainAnalysisComplete &&
            workflowStep === "segmentation" &&
            "Terrain Analysis Complete"}
          {workflowStep === "heatmap" && "Probability Mapping"}
          {workflowStep === "complete" &&
            !terrainAnalysisComplete &&
            "Terrain Analysis Complete"}
          {workflowStep === "complete" &&
            terrainAnalysisComplete &&
            heatmapData && (
              <div className="flex items-center justify-between">
                <button
                  onClick={switchToSegmentationView}
                  disabled={currentView === "segmentation"}
                  className={`p-1 rounded ${
                    currentView === "segmentation"
                      ? "text-gray-400 cursor-not-allowed"
                      : "text-black hover:bg-gray-100"
                  }`}
                >
                  ←
                </button>
                <span className="text-sm">
                  {currentView === "segmentation"
                    ? "Terrain Analysis"
                    : "Probability Heatmap"}
                </span>
                <button
                  onClick={switchToHeatmapView}
                  disabled={currentView === "heatmap"}
                  className={`p-1 rounded ${
                    currentView === "heatmap"
                      ? "text-gray-400 cursor-not-allowed"
                      : "text-black hover:bg-gray-100"
                  }`}
                >
                  →
                </button>
              </div>
            )}
        </h2>

        {/* Interactive Progress Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm font-medium text-gray-700">
              {!terrainAnalysisComplete &&
                workflowStep === "segmentation" &&
                "25%"}
              {terrainAnalysisComplete && !heatmapData && "50%"}
              {workflowStep === "heatmap" && "75%"}
              {workflowStep === "complete" && heatmapData && "100%"}
            </span>
          </div>

          {/* Animated Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-3 overflow-hidden">
            <div
              className={`bg-black h-2 rounded-full transition-all duration-1000 ease-out ${
                !terrainAnalysisComplete && workflowStep === "segmentation"
                  ? "w-1/4"
                  : terrainAnalysisComplete && !heatmapData
                  ? "w-1/2"
                  : workflowStep === "heatmap"
                  ? "w-3/4"
                  : workflowStep === "complete" && heatmapData
                  ? "w-full"
                  : "w-0"
              }`}
            ></div>
          </div>

          {/* Current Step Display */}
          <div className="text-center">
            {!terrainAnalysisComplete && workflowStep === "segmentation" && (
              <div className="flex items-center justify-center space-x-2 text-gray-600">
                <div className="animate-spin rounded-full h-3 w-3 border-2 border-gray-400 border-b-transparent"></div>
                <span className="text-xs">Analyzing satellite imagery...</span>
              </div>
            )}
            {terrainAnalysisComplete && !heatmapData && (
              <div className="flex items-center justify-center space-x-2 text-green-600">
                <div className="rounded-full h-3 w-3 bg-green-500"></div>
                <span className="text-xs">Terrain analysis complete</span>
              </div>
            )}
            {workflowStep === "heatmap" && (
              <div className="flex items-center justify-center space-x-2 text-gray-600">
                <div className="animate-bounce rounded-full h-3 w-3 bg-gray-400"></div>
                <span className="text-xs">
                  Computing search probabilities...
                </span>
              </div>
            )}
            {workflowStep === "complete" && heatmapData && (
              <div className="flex items-center justify-center space-x-2 text-green-600">
                <div className="rounded-full h-3 w-3 bg-green-500"></div>
                <span className="text-xs">
                  Viewing:{" "}
                  {currentView === "segmentation"
                    ? "Terrain Layers"
                    : "Search Probabilities"}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-3">
          {/* Analysis Area Info */}
          {boundingBox && (
            <div className="text-xs text-gray-600 p-2 bg-gray-50 rounded">
              <p className="font-medium mb-1">Analysis Area:</p>
              <div className="grid grid-cols-2 gap-1 text-xs">
                <p>N: {boundingBox.north.toFixed(4)}</p>
                <p>S: {boundingBox.south.toFixed(4)}</p>
                <p>E: {boundingBox.east.toFixed(4)}</p>
                <p>W: {boundingBox.west.toFixed(4)}</p>
              </div>
              <p className="text-xs mt-1">
                Area: {calculateArea(boundingBox).toFixed(1)} km²
              </p>
            </div>
          )}

          {/* Loading Status */}
          {loading && (
            <div className="text-center p-3 bg-gray-50 rounded border">
              <div className="flex items-center justify-center space-x-3">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-black border-b-transparent"></div>
                <div>
                  <div className="text-sm font-medium text-black">
                    {workflowStep === "segmentation" &&
                      "Processing Satellite Data"}
                    {workflowStep === "heatmap" && "Generating Heat Map"}
                    {workflowStep === "flightpath" && "Planning Flight Path"}
                    {workflowStep === "complete" && "Analysis Complete"}
                  </div>
                  <div className="text-xs text-gray-500">
                    {workflowStep === "segmentation" &&
                      "Identifying terrain features"}
                    {workflowStep === "heatmap" && "Computing probabilities"}
                    {workflowStep === "flightpath" && "Optimizing waypoints"}
                    {workflowStep === "complete" && "Ready for operations"}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Heatmap Info */}
          {heatmapData &&
            workflowStep === "complete" &&
            currentView === "heatmap" && (
              <div className="text-xs p-2 bg-orange-50 border border-orange-200 rounded">
                <p className="font-medium text-orange-700 mb-1">
                  Probability Heatmap
                </p>
                <p className="text-orange-600">
                  Search Points: {heatmapData.coordinates?.length || 0}
                </p>
                <p className="text-orange-600 mb-2">Area Coverage: Complete</p>

                {/* Heatmap Legend */}
                <div className="border-t border-orange-200 pt-2">
                  <p className="font-medium text-orange-700 mb-1">
                    Search Probability
                  </p>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-white border border-gray-300 rounded"></div>
                      <span className="text-gray-600">No Activity</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-yellow-300 rounded"></div>
                      <span className="text-gray-600">Low</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-orange-400 rounded"></div>
                      <span className="text-gray-600">Medium</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-red-600 rounded"></div>
                      <span className="text-gray-600">High</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

          {/* Flight Path Info */}
          {flightPathData &&
            workflowStep === "complete" &&
            currentView === "flightpath" && (
              <div className="text-xs p-2 bg-red-50 border border-red-200 rounded">
                <p className="font-medium text-red-700 mb-1">
                  Drone Flight Plan
                </p>
                <p className="text-red-600">
                  Waypoints: {flightPathData.flight_path?.length || 0}
                </p>
                <p className="text-red-600">
                  Hotspots: {flightPathData.num_hotspots || 0}
                </p>
                <p className="text-red-600 mb-2">Flight Time: {flightPathData.estimated_time || "Calculated based on waypoints"}</p>

                {/* Flight Path Legend */}
                <div className="border-t border-red-200 pt-2">
                  <p className="font-medium text-red-700 mb-1">
                    Flight Elements
                  </p>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-gray-600">Start Point</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-blue-500 rounded-full"></div>
                      <span className="text-gray-600">Waypoints</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-red-500 rounded-full"></div>
                      <span className="text-gray-600">End Point</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-1 bg-red-600 rounded"></div>
                      <span className="text-gray-600">Flight Path</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

          {/* Segmentation Info */}
          {Object.keys(animatedLayers).length > 0 &&
            workflowStep === "complete" &&
            currentView === "segmentation" && (
              <div className="text-xs p-2 bg-blue-50 border border-blue-200 rounded">
                <p className="font-medium text-blue-700 mb-1">Terrain Layers</p>
                <p className="text-blue-600 mb-2">
                  Available:{" "}
                  {Object.keys(animatedLayers).join(", ").replace(/_/g, " ")}
                </p>

                {/* Terrain Legend */}
                <div className="border-t border-blue-200 pt-2">
                  <p className="font-medium text-blue-700 mb-1">Legend</p>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-blue-500 rounded"></div>
                      <span className="text-gray-600">Water Bodies</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-green-300 rounded"></div>
                      <span className="text-gray-600">Sparse Forest</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-green-700 rounded"></div>
                      <span className="text-gray-600">Dense Forest</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-2 bg-gray-700 rounded"></div>
                      <span className="text-gray-600">Roads</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

          {/* Animation Status */}
          {animationActive && (
            <div className="text-center p-2 bg-green-50 rounded border border-green-200">
              <div className="text-xs text-green-600 font-medium">
                Animation Running... ({animationProgress}%)
              </div>
            </div>
          )}

          {/* Simple Controls */}
          <div className="flex space-x-2">
            {terrainAnalysisComplete && !heatmapData ? (
              <button
                className="w-full bg-black hover:bg-gray-800 text-white px-4 py-2 rounded font-medium transition-colors duration-200"
                onClick={generateHeatmapAndFlightPlan}
                disabled={loading}
              >
                Continue to Heatmap
              </button>
            ) : heatmapComplete && !flightPathData ? (
              <button
                className="w-full bg-black hover:bg-gray-800 text-white px-4 py-2 rounded font-medium transition-colors duration-200"
                onClick={generateFlightPath}
                disabled={loading}
              >
                Generate Flight Path
              </button>
            ) : boundingBox &&
              !loading &&
              !Object.keys(animatedLayers).length ? (
              <button
                className="w-full bg-black hover:bg-gray-800 text-white px-4 py-2 rounded font-medium transition-colors duration-200"
                onClick={generateAnimatedLayers}
              >
                Generate Analysis
              </button>
            ) : null}
          </div>

          {/* View Navigation Controls - Only show when all analysis is complete */}
          {workflowStep === "complete" && heatmapData && flightPathData && (
            <div className="flex space-x-2">
              <button
                onClick={switchToSegmentationViewUpdated}
                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors duration-200 ${
                  currentView === "segmentation"
                    ? "bg-black text-white"
                    : "bg-white text-black border border-gray-300 hover:bg-gray-100"
                }`}
              >
                Terrain
              </button>
              <button
                onClick={switchToHeatmapViewUpdated}
                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors duration-200 ${
                  currentView === "heatmap"
                    ? "bg-black text-white"
                    : "bg-white text-black border border-gray-300 hover:bg-gray-100"
                }`}
              >
                Heatmap
              </button>
              <button
                onClick={switchToFlightPathView}
                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors duration-200 ${
                  currentView === "flightpath"
                    ? "bg-black text-white"
                    : "bg-white text-black border border-gray-300 hover:bg-gray-100"
                }`}
              >
                Flight Path
              </button>
            </div>
          )}

          {/* Focus Mask Control */}
          {Object.keys(animatedLayers).length > 0 && (
            <button
              onClick={() => {
                if (maskOverlay) {
                  if (Array.isArray(maskOverlay)) {
                    maskOverlay.forEach((overlay) => overlay.setMap(null));
                  } else {
                    maskOverlay.setMap(null);
                  }
                  setMaskOverlay(null);
                } else {
                  createMaskOverlay();
                }
              }}
              className="w-full bg-white hover:bg-gray-100 text-black border border-gray-300 px-3 py-2 rounded font-medium transition-colors duration-200 text-sm"
            >
              {maskOverlay ? "Remove Focus Mask" : "Add Focus Mask"}
            </button>
          )}
          <Link
            href={`/find_match?id=${window.location.href.slice(-8)}
              `}
            target="_blank"
            className="w-full bg-white hover:bg-gray-100 text-black border border-gray-300 px-3 py-2 rounded font-medium transition-colors duration-200 text-sm"
          >
            View Drone Images
          </Link>
        </div>
      </div>

      {/* Map Controls */}
      <div className="absolute bottom-8 left-8 flex flex-col gap-2 z-10">
        {/* Map Type Toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => {
              if (mapInstance) {
                mapInstance.setMapTypeId("roadmap");
                mapInstance.setOptions({ styles: darkAppleStyle });
              }
            }}
            className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700"
          >
            Road Map
          </button>
          <button
            onClick={() => {
              if (mapInstance) {
                mapInstance.setMapTypeId("satellite");
                mapInstance.setOptions({ styles: null });
              }
            }}
            className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700"
          >
            Satellite
          </button>
        </div>
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-20">
          <div className="bg-white p-6 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="text-gray-700">
                Generating analysis overlay...
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
