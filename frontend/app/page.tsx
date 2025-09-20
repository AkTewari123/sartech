"use client";

import { useEffect, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

export default function Home() {
  const [path, setPath] = useState<{ lat: number; lng: number }[]>([]);
  const [mapInstance, setMapInstance] = useState<any | null>(null);
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

  // Fetch flight path from API
  useEffect(() => {
    async function fetchPath() {
      const res = await fetch("/api/flightpath");
      const data = await res.json();
      setPath(data.path);
    }
    fetchPath();
  }, []);

  // Dark Apple-like style for map
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

  // Draw flight path polyline
  const drawFlightPath = (map: any) => {
    new window.google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: "#3199F9",
      strokeOpacity: 1,
      strokeWeight: 7,
      map,
    });
    new window.google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: "#0273F8",
      strokeOpacity: 1,
      strokeWeight: 4,
      map,
    });
  };

  // Initialize Google Map + Drone Model
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
          tilt: 0,
        }
      );

      drawFlightPath(map);
      setMapInstance(map);

      // WebGLOverlayView for 3D Drone
      const overlay = new window.google.maps.WebGLOverlayView();

      overlay.onAdd = () => {
        overlay.scene = new THREE.Scene();
        overlay.camera = new THREE.PerspectiveCamera();

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        overlay.scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
        dirLight.position.set(0, 10, 0);
        overlay.scene.add(dirLight);

        // Load drone model from drones/
        const loader = new GLTFLoader();
        loader.load(
          "/drones/drone_model.gltf",
          (gltf: any) => {
            overlay.droneModel = gltf.scene;
            overlay.scene.add(overlay.droneModel);
          },
          undefined,
          (err: ErrorEvent) => err
        );
      };

      overlay.onContextRestored = ({ gl }: any) => {
        overlay.renderer = new THREE.WebGLRenderer({
          canvas: gl.canvas,
          context: gl,
          ...gl.getContextAttributes(),
        });
        overlay.renderer.autoClear = false;
      };

      overlay.onDraw = ({ gl, transformer }: any) => {
        if (!overlay.droneModel) return;

        // Position drone at first path point (altitude = 50)
        const { lat, lng } = path[0];
        const coords = transformer.latLngAltitudeToWorld({
          lat,
          lng,
          altitude: 50,
        });
        overlay.droneModel.position.set(coords.x, coords.y, coords.z);

        overlay.renderer.render(overlay.scene, overlay.camera);
        overlay.renderer.resetState();
      };

      overlay.setMap(map);
    };

    // Load Google Maps script
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

  // 2D map toggle
  const enable2D = () => {
    if (mapInstance) {
      mapInstance.setMapTypeId("roadmap");
      mapInstance.setTilt(0);
      mapInstance.setHeading(0);
      mapInstance.setOptions({ styles: darkAppleStyle });
    }
  };

  // 3D map toggle
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
