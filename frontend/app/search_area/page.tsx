"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";

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
      const response = await fetch("http://localhost:8000/generate-layers", {
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
          console.log("Animation cycle complete");
          setAnimationActive(false);
          animationRef.current.active = false;
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
        setAnimationProgress(currentStep + 1);

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
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initSearchMap`;
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
      <div className="absolute top-1/2 left-8 transform -translate-y-1/2 bg-white min-w-[325px] p-4 rounded-lg shadow-lg z-10 max-w-sm">
        <h2 className="text-lg font-semibold mb-4">Segmentation Analysis</h2>

        <div className="space-y-4">
          {/* Analysis Area Info */}
          {boundingBox && (
            <div className="text-sm text-gray-600 p-3 bg-gray-50 rounded">
              <p>
                <strong>Analysis Area:</strong>
              </p>
              <p>North: {boundingBox.north.toFixed(6)}</p>
              <p>South: {boundingBox.south.toFixed(6)}</p>
              <p>East: {boundingBox.east.toFixed(6)}</p>
              <p>West: {boundingBox.west.toFixed(6)}</p>
              <p>Area: {calculateArea(boundingBox).toFixed(2)} km²</p>
              {isZoomedIn && (
                <div className="text-blue-600 font-medium mt-2">
                  📍 Zoomed to Analysis Area
                </div>
              )}
            </div>
          )}

          {/* Loading Status */}
          {loading && (
            <div className="text-center p-4 bg-blue-50 rounded">
              <div className="flex items-center justify-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <div>
                  <div className="text-sm text-blue-600 font-medium">
                    Generating segmentation layers...
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    This may take a few moments
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Animation Status */}
          {animationActive && (
            <div className="text-center p-4 bg-green-50 rounded">
              <div className="text-sm text-green-600 font-medium">
                Animation in progress...
              </div>
              <div className="text-xs text-gray-500 mt-2">
                {layerOrder.map((layer: string, idx: number) => (
                  <span
                    key={layer}
                    className={
                      animationProgress > idx
                        ? "text-green-600"
                        : "text-gray-400"
                    }
                  >
                    {layer} {animationProgress > idx ? "✓" : "○"}
                    {idx < layerOrder.length - 1 ? " → " : ""}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Available Layers Info */}
          {Object.keys(animatedLayers).length > 0 && !animationActive && (
            <div className="text-sm text-gray-600 p-3 bg-gray-50 rounded">
              <p>
                <strong>Ready Layers:</strong>
              </p>
              <div className="text-xs text-gray-500 mt-1">
                {Object.keys(animatedLayers).join(", ")}
              </div>
            </div>
          )}

          {/* Legend */}
          {Object.keys(animatedLayers).length > 0 && (
            <div className="text-sm p-3 bg-gray-50 rounded">
              <p className="font-semibold mb-2 text-gray-700">Legend</p>
              <div className="space-y-1 text-xs">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-3 bg-blue-500 rounded"></div>
                  <span className="text-gray-600">Water Bodies</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-3 bg-green-300 rounded"></div>
                  <span className="text-gray-600">Sparse Forest</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-3 bg-green-700 rounded"></div>
                  <span className="text-gray-600">Dense Forest</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-3 bg-yellow-600 rounded"></div>
                  <span className="text-gray-600">Roads</span>
                </div>
              </div>
            </div>
          )}

          {/* Simple Controls */}
          <div className="flex space-x-2">
            {Object.keys(animatedLayers).length > 0 ? (
              <>
                <button
                  className="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-[14px] px-4 py-2 rounded disabled:opacity-50"
                  onClick={startAnimation}
                  disabled={animationActive}
                >
                  {animationActive ? "Running..." : "Start Animation"}
                </button>
                <button
                  className="flex-1 bg-rose-500 hover:bg-rose-600 text-white px-4 py-2 rounded"
                  onClick={clearAllLayers}
                >
                  Clear
                </button>
              </>
            ) : boundingBox && !loading ? (
              <button
                className="w-full bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded"
                onClick={generateAnimatedLayers}
              >
                Generate Analysis
              </button>
            ) : null}
          </div>

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
              className="w-full bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded text-sm"
            >
              {maskOverlay ? "Remove" : "Add"} Focus Mask
            </button>
          )}
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
