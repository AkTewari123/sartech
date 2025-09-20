"use client";

import { useEffect, useRef } from "react";

interface LatLng {
  lat: number;
  lng: number;
}

export default function Home() {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const flightPathRef = useRef<any>(null);

  useEffect(() => {
    const initMap = () => {
      if (!mapRef.current) return;

      const start: LatLng = { lat: 40.742, lng: -74.177 };

      const mapInstance = new window.google.maps.Map(mapRef.current, {
        zoom: 14,
        center: { lat: 40.742, lng: -74.177 },
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
      });

      const flightPath = new window.google.maps.Polyline({
        path: [],
        geodesic: true,
        strokeColor: "#FF0000",
        strokeOpacity: 1.0,
        strokeWeight: 3,
      });

      flightPath.setMap(mapInstance);
      flightPathRef.current = flightPath;
    };

    const existingScript = document.getElementById("google-maps-script");
    if (!existingScript) {
      const script = document.createElement("script");
      script.id = "google-maps-script";
      script.src = `https://maps.googleapis.com/maps/api/js?key=AIzaSyAYvkRDug28EqDoxLSgwBAyLc62xLblD4c&callback=initMap`;
      script.async = true;
      script.defer = true;
      window.initMap = initMap;
      document.body.appendChild(script);
    } else if (window.google) {
      initMap();
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      if (!flightPathRef.current) return;

      try {
        const res = await fetch("/api/flightpath");
        const data: { path: LatLng[] } = await res.json();
        flightPathRef.current.setPath(data.path);
      } catch (err) {
        console.error("Failed to fetch flight path:", err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return <div ref={mapRef} className="w-full h-screen" />;
}
