"use client";

import { useEffect, useState } from "react";

export default function SearchArea() {
  const [mapInstance, setMapInstance] = useState<any | null>(null);
  const [drawingManager, setDrawingManager] = useState<any | null>(null);
  const [currentRectangle, setCurrentRectangle] = useState<any | null>(null);
  const [boundingBox, setBoundingBox] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
  } | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [overlayVisible, setOverlayVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [currentOverlay, setCurrentOverlay] = useState<any>(null);
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

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

  // Generate overlay image from your API
  const generateOverlay = async () => {
    if (!boundingBox) return;
    
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/generate-map', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(boundingBox),
      });

      if (response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        
        // Remove existing overlay
        if (currentOverlay) {
          currentOverlay.setMap(null);
        }

        // Create new overlay
        const overlay = new window.google.maps.GroundOverlay(
          imageUrl,
          {
            north: boundingBox.north,
            south: boundingBox.south,
            east: boundingBox.east,
            west: boundingBox.west,
          },
          {
            opacity: 0.7,
          }
        );
        
        overlay.setMap(mapInstance);
        setCurrentOverlay(overlay);
        setOverlayVisible(true);
      } else {
        console.error('Failed to generate overlay');
      }
    } catch (error) {
      console.error('Error generating overlay:', error);
    } finally {
      setLoading(false);
    }
  };

  // Toggle overlay visibility
  const toggleOverlay = () => {
    if (currentOverlay) {
      if (overlayVisible) {
        currentOverlay.setMap(null);
        setOverlayVisible(false);
      } else {
        currentOverlay.setMap(mapInstance);
        setOverlayVisible(true);
      }
    }
  };

  // Clear bounding box and overlay
  const clearSelection = () => {
    setBoundingBox(null);
    if (currentOverlay) {
      currentOverlay.setMap(null);
      setCurrentOverlay(null);
    }
    if (currentRectangle) {
      currentRectangle.setMap(null);
      setCurrentRectangle(null);
    }
    setOverlayVisible(false);
    setIsDrawing(false);
  };

  // Enable bounding box drawing
  const enableDrawing = () => {
    if (drawingManager) {
      clearSelection();
      setIsDrawing(true);
      drawingManager.setDrawingMode(window.google.maps.drawing.OverlayType.RECTANGLE);
    }
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
          mapTypeId: "roadmap",
          styles: darkAppleStyle,
          tilt: 0,
        }
      );

      setMapInstance(map);

      // Add drawing manager for bounding box selection
      const manager = new window.google.maps.drawing.DrawingManager({
        drawingMode: null,
        drawingControl: false,
        rectangleOptions: {
          fillColor: '#3199F9',
          fillOpacity: 0.2,
          strokeColor: '#3199F9',
          strokeOpacity: 0.8,
          strokeWeight: 2,
          clickable: false,
          editable: true,
        },
      });

      manager.setMap(map);
      setDrawingManager(manager);

      // Handle rectangle completion
      manager.addListener('rectanglecomplete', (rectangle: any) => {
        // Remove any existing rectangle
        if (currentRectangle) {
          currentRectangle.setMap(null);
        }
        setCurrentRectangle(rectangle);

        const bounds = rectangle.getBounds();
        const ne = bounds.getNorthEast();
        const sw = bounds.getSouthWest();
        
        setBoundingBox({
          north: ne.lat(),
          south: sw.lat(),
          east: ne.lng(),
          west: sw.lng(),
        });
        
        setIsDrawing(false);
        manager.setDrawingMode(null);

        // Update bounding box when rectangle is edited
        rectangle.addListener('bounds_changed', () => {
          const newBounds = rectangle.getBounds();
          const newNe = newBounds.getNorthEast();
          const newSw = newBounds.getSouthWest();
          
          setBoundingBox({
            north: newNe.lat(),
            south: newSw.lat(),
            east: newNe.lng(),
            west: newSw.lng(),
          });
        });
      });
    };

    // Load Google Maps script with drawing library
    if (!document.getElementById("google-maps-search-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-search-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=drawing&callback=initSearchMap`;
      script.async = true;
      script.defer = true;
      // @ts-ignore
      window.initSearchMap = initMap;
      document.body.appendChild(script);
    } else {
      // @ts-ignore
      if (window.google && window.google.maps && window.google.maps.drawing) {
        initMap();
      }
    }
  }, [apiKey]);

  return (
    <div className="relative w-full h-screen m-0 p-0">
      <div id="search-map" style={{ width: "100%", height: "100%" }} />
      
      {/* Control Panel */}
      <div className="absolute top-8 left-8 bg-gray-800 p-4 rounded-lg shadow-lg z-10 min-w-80">
        <h2 className="text-white text-lg font-semibold mb-4">Search Area Analysis</h2>
        
        {/* Drawing Controls */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={enableDrawing}
            disabled={isDrawing || !drawingManager}
            className={`px-4 py-2 rounded text-sm font-medium ${
              isDrawing || !drawingManager
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {!drawingManager ? 'Loading...' : isDrawing ? 'Click & Drag on Map' : 'Draw Bounding Box'}
          </button>
          <button
            onClick={clearSelection}
            className="px-4 py-2 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-700"
          >
            Clear
          </button>
        </div>

        {/* Bounding Box Info */}
        {boundingBox && (
          <div className="mb-4">
            <h3 className="text-white text-sm font-medium mb-2">Selected Area:</h3>
            <div className="text-gray-300 text-xs space-y-1">
              <div>North: {boundingBox.north.toFixed(6)}</div>
              <div>South: {boundingBox.south.toFixed(6)}</div>
              <div>East: {boundingBox.east.toFixed(6)}</div>
              <div>West: {boundingBox.west.toFixed(6)}</div>
            </div>
          </div>
        )}

        {/* Analysis Controls */}
        {boundingBox && (
          <div className="flex gap-2 mb-4">
            <button
              onClick={generateOverlay}
              disabled={loading}
              className={`px-4 py-2 rounded text-sm font-medium ${
                loading 
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              {loading ? 'Analyzing...' : 'Analyze Area'}
            </button>
            
            {currentOverlay && (
              <button
                onClick={toggleOverlay}
                className="px-4 py-2 bg-yellow-600 text-white rounded text-sm font-medium hover:bg-yellow-700"
              >
                {overlayVisible ? 'Hide Overlay' : 'Show Overlay'}
              </button>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="text-gray-400 text-xs">
          <p className="mb-2">Instructions:</p>
          <ol className="space-y-1">
            <li>1. Click "Draw Bounding Box"</li>
            <li>2. Draw rectangle on map</li>
            <li>3. Click "Analyze Area" for overlay</li>
            <li>4. Toggle overlay visibility as needed</li>
          </ol>
        </div>
      </div>

      {/* Map Type Toggle */}
      <div className="absolute bottom-8 left-8 flex gap-2 z-10">
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
      
      {/* Loading Indicator */}
      {loading && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-20">
          <div className="bg-white p-6 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="text-gray-700">Generating analysis overlay...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
