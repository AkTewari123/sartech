"use client";

import { useEffect, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

export default function Home() {
  const [path, setPath] = useState<{ lat: number; lng: number }[]>([]);
  const [mapInstance, setMapInstance] = useState<any | null>(null);

  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;
  const mapId = process.env.NEXT_PUBLIC_MAP_ID; // 3D Tiles Map ID

  // Styling to remove all labels/icons for 3D Tiles
  const clean3DStyle = [
    { featureType: "all", elementType: "labels", stylers: [{ visibility: "off" }] },
    { featureType: "all", elementType: "labels.icon", stylers: [{ visibility: "off" }] },
    { featureType: "poi", elementType: "all", stylers: [{ visibility: "off" }] },
    { featureType: "administrative", elementType: "all", stylers: [{ visibility: "off" }] },
    { featureType: "road", elementType: "labels", stylers: [{ visibility: "off" }] },
  ];

  // Fetch flight path
  useEffect(() => {
    async function fetchPath() {
      const res = await fetch("/api/flightpath");
      const data = await res.json();
      setPath(data.path);
    }
    fetchPath();
  }, []);

  // Draw flight path
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

  useEffect(() => {
    if (!path.length || !apiKey || !mapId) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("map") as HTMLElement,
        {
          center: path[0],
          zoom: 9,
          tilt: 65,
          heading: 0,
          mapId: mapId,
          // Remove labels/icons via styles and disable UI controls to prevent switching to 2D/terrain
          styles: clean3DStyle, // ✅ remove labels/icons
          disableDefaultUI: true,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          clickableIcons: false,
          gestureHandling: "greedy",
        }
      );

      drawFlightPath(map);
      setMapInstance(map);

      // WebGLOverlayView for drone
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

        // Load drone model
        const loader = new GLTFLoader();
        loader.load(
  "/drone/scene.gltf",   // correct path
  (gltf: any) => {
    overlay.droneModel = gltf.scene;
    overlay.droneModel.scale.set(50, 50, 50); // make it visible
    overlay.scene.add(overlay.droneModel);
  },
  undefined,
  (err: ErrorEvent) => console.error(err)
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

      // Animate drone
      let index = 0;
      overlay.onDraw = ({ transformer }: any) => {
        if (!overlay.droneModel) return;

        const { lat, lng } = path[index];
        const coords = transformer.latLngAltitudeToWorld({
          lat,
          lng,
          altitude: 50,
        });
        overlay.droneModel.position.set(coords.x, coords.y, coords.z);

        if (index < path.length - 1) {
          const { lat: nLat, lng: nLng } = path[index + 1];
          const next = transformer.latLngAltitudeToWorld({
            lat: nLat,
            lng: nLng,
            altitude: 50,
          });
          overlay.droneModel.lookAt(next.x, next.y, next.z);
        }

        overlay.renderer.render(overlay.scene, overlay.camera);
        overlay.renderer.resetState();

        index = (index + 1) % path.length;
      };

      overlay.setMap(map);
    };

    // Load Maps script
    if (!document.getElementById("google-maps-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&map_ids=${mapId}&v=beta&callback=initMap`;
      script.async = true;
      script.defer = true;
      // @ts-ignore
      window.initMap = initMap;
      document.body.appendChild(script);
    } else {
      // @ts-ignore
      if (window.google) initMap();
    }
  }, [path, apiKey, mapId]);

  return (
    <div className="relative w-full h-screen">
      <div id="map" style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
