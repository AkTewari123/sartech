"use client";

import { useEffect, useState } from "react";

type LatLng = { lat: number; lng: number; weight?: number };

export default function Home() {
  const [mapInstance, setMapInstance] = useState<any>(null);
  const [heatData, setHeatData] = useState<LatLng[]>([]);
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

  useEffect(() => {
    async function fetchProbabilities() {
      try {
        const res = await fetch("/api/probabilities");
        const data = await res.json();
        setHeatData(data.probabilities); // [{lat, lng, prob}]
      } catch {
        // fallback sample
        setHeatData([
          { lat: 40.7128, lng: -74.006, weight: 0.9 },
          { lat: 40.715, lng: -74.002, weight: 0.4 },
          { lat: 40.718, lng: -74.004, weight: 0.6 },
        ]);
      }
    }
    fetchProbabilities();
  }, []);

  useEffect(() => {
    if (!apiKey) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("map") as HTMLElement,
        {
          center: { lat: 40.7128, lng: -74.006 },
          zoom: 15,
          mapTypeId: "satellite",
        }
      );

      setMapInstance(map);

      // Heatmap Layer
      const heatmap = new window.google.maps.visualization.HeatmapLayer({
        data: heatData.map((p) => ({
          location: new window.google.maps.LatLng(p.lat, p.lng),
          weight: p.weight ?? 1,
        })),
        radius: 50, // radius in pixels
        opacity: 0.7, // transparency
        gradient: [
          "rgba(0, 0, 255, 0)", // low
          "rgba(0, 255, 255, 1)",
          "rgba(0, 255, 0, 1)",
          "rgba(255, 255, 0, 1)",
          "rgba(255, 0, 0, 1)", // high
        ],
      });

      heatmap.setMap(map);
    };

    if (!document.getElementById("google-maps-script")) {
      const script = document.createElement("script");
      script.id = "google-maps-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=visualization`;
      script.async = true;
      script.defer = true;
      script.onload = initMap;
      document.body.appendChild(script);
    } else {
      if (window.google) initMap();
    }
  }, [apiKey, heatData]);

  return <div id="map" style={{ width: "100%", height: "100vh" }} />;
}
