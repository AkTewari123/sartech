"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [path, setPath] = useState<{ lat: number; lng: number }[]>([]);
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API; // ✅ Exposed client-side

  useEffect(() => {
    async function loadPath() {
      const res = await fetch("/api/flightpath");
      const data = await res.json();
      setPath(data.path);
    }
    loadPath();
  }, []);

  useEffect(() => {
    if (!path.length || !apiKey) return;

    const initMap = () => {
      const map = new window.google.maps.Map(
        document.getElementById("map") as HTMLElement,
        {
          zoom: 14,
          center: path[0],
          mapTypeId: "roadmap",
          styles: [
            {
              elementType: "geometry",
              stylers: [{ color: "#1d1d1d" }], // background similar to Apple Maps dark
            },
            {
              elementType: "labels.text.fill",
              stylers: [{ color: "#f5f5f7" }], // light gray labels
            },
            {
              elementType: "labels.text.stroke",
              stylers: [{ color: "#1d1d1d" }], // match background
            },
            {
              featureType: "road",
              elementType: "geometry",
              stylers: [{ color: "#2c2c2c" }], // dark gray roads
            },
            {
              featureType: "road",
              elementType: "geometry.stroke",
              stylers: [{ color: "#3a3a3a" }], // subtle borders
            },
            {
              featureType: "water",
              elementType: "geometry",
              stylers: [{ color: "#0b3d91" }], // deep blue water like Apple Maps dark
            },
            {
              featureType: "poi",
              elementType: "labels",
              stylers: [{ visibility: "off" }], // Apple Maps is clean
            },
            {
              featureType: "transit",
              elementType: "labels",
              stylers: [{ visibility: "off" }],
            },
            {
              featureType: "landscape.man_made",
              elementType: "geometry",
              stylers: [{ color: "#1d1d1d" }],
            },
            {
              featureType: "landscape.natural",
              elementType: "geometry",
              stylers: [{ color: "#1a1a1a" }],
            },
          ],
        }
      );

      const flightPath = new window.google.maps.Polyline({
        path,
        geodesic: true,
        strokeColor: "#FF0000",
        strokeOpacity: 1.0,
        strokeWeight: 3,
      });

      flightPath.setMap(map);
    };

    const existingScript = document.getElementById("google-maps-script");
    if (!existingScript) {
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

  return <div id="map" className="w-full h-screen" />;
}
