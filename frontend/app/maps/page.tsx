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

  //--- Add this helper for heatmap
  const addHeatmap = (map: any, points: { lat: number; lng: number }[]) => {
    if (!window.google?.maps?.visualization) return;
    const heatmap = new window.google.maps.visualization.HeatmapLayer({
      data: points.map(
        pt => new window.google.maps.LatLng(pt.lat, pt.lng)
      ),
      radius: 10000,
      opacity: 0.7,
    });
    heatmap.setMap(map);
  };

  // Dark Apple-like style for map
  // const darkAppleStyle = [
  //   // ... (your existing dark Apple style array here)
  // ];

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

  // Initialize Google Map + Drone Model + Heatmap
  useEffect(() => {
    if (!path.length || !apiKey) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("map") as HTMLElement,
        {
          center: path[0],
          zoom: 14,
          mapTypeId: "roadmap",
          // styles: darkAppleStyle,
          tilt: 0,
        }
      );

      drawFlightPath(map);

      addHeatmap(map, path); // <----- add heatmap overlay here

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

        // Load drone model from /drones/
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

    // Load Google Maps script with visualization library
    if (!document.getElementById("google-maps-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap&libraries=visualization`;
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
      // mapInstance.setOptions({ styles: darkAppleStyle });
    }
  };

  // 3D map toggle
  const enable3D = () => {
    if (mapInstance) {
      mapInstance.setMapTypeId("satellite");
      mapInstance.setTilt(60);
      mapInstance.setHeading(0);
      // mapInstance.setOptions({ styles: darkAppleStyle });
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
