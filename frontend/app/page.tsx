"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [path, setPath] = useState<{ lat: number; lng: number }[]>([]);
  const [mapInstance, setMapInstance] = useState<any | null>(null);
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

  // Fetch the flight path from your API
  useEffect(() => {
    async function loadPath() {
      const res = await fetch("/api/flightpath");
      const data = await res.json();
      setPath(data.path);
    }
    loadPath();
  }, []);

  // Dark Apple-like style for 2D and 3D
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

  // Draw polyline with outline trick
  const drawFlightPath = (map: any) => {
    // Outline
    new window.google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: "#3199F9",
      strokeOpacity: 1.0,
      strokeWeight: 7,
      map,
    });

    // Interior
    new window.google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: "#0273F8",
      strokeOpacity: 1.0,
      strokeWeight: 4,
      map,
    });
  };

  // Initialize Google Map
  useEffect(() => {
    if (!path.length || !apiKey) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("map") as HTMLElement,
        {
          center: path[0],
          zoom: 14,
          mapTypeId: "roadmap",
          styles: darkAppleStyle,
        }
      );

      drawFlightPath(map);
      setMapInstance(map);
    };

    if (!document.getElementById("google-maps-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap`;
      script.async = true;
      script.defer = true;
      // @ts-ignore
      window.initMap = initMap;
      document.body.appendChild(script);
    } else {
      // @ts-ignore
      if (window.google) initMap();
    }
  }, [path, apiKey]);

  // 2D toggle
  const enable2D = () => {
    if (mapInstance) {
      mapInstance.setMapTypeId("roadmap");
      mapInstance.setTilt(0);
      mapInstance.setHeading(0);
      mapInstance.setOptions({ styles: darkAppleStyle });
    }
  };

  // 3D toggle
  const enable3D = () => {
    if (mapInstance) {
      mapInstance.setMapTypeId("satellite");
      mapInstance.setTilt(60);
      mapInstance.setHeading(0);
      mapInstance.setOptions({ styles: darkAppleStyle });
      mapInstance.setZoom(Math.max(mapInstance.getZoom() || 18, 18));
    }
  };

  return (
    <div className="relative w-full h-screen m-0 p-0">
      <div id="map" style={{ width: "100%", height: "100%" }} />
      <div className="absolute bottom-8 left-8 flex gap-2 z-10">
        <button
          onClick={enable2D}
          className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700"
        >
          2D Dark
        </button>
        <button
          onClick={enable3D}
          className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700"
        >
          3D Dark
        </button>
      </div>
    </div>
  );
}
