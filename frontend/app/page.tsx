"use client";
import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
// import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";

type FormData = {
  name: string;
  hasMentalInjury: boolean;
  latitude: string;
  longitude: string;
  locationQuery: string;
  imageFile: FileList | null;
  lastSeenClothing: string;
};

export default function MissingPersonForm() {
  const [mapReady, setMapReady] = useState(false);
  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any | null>(null);
  const markerRef = useRef<any | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: "",
      hasMentalInjury: false,
      latitude: "",
      longitude: "",
      locationQuery: "",
      imageFile: null,
      lastSeenClothing: "",
    },
  });

  const lat = watch("latitude");
  const lng = watch("longitude");
  const locationQuery = watch("locationQuery");
  const apiKey = process.env.NEXT_PUBLIC_MAPS_API;

  // Load Google Maps JS
  useEffect(() => {
    if (!apiKey) return;
    if ((window as any).google?.maps) {
      setMapReady(true);
      return;
    }
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}`;
    script.async = true;
    script.defer = true;
    script.onload = () => setMapReady(true);
    document.head.appendChild(script);
  }, [apiKey]);

  // Initialize map
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    const center = { lat: 40.7128, lng: -74.006 };
    mapInstanceRef.current = new (window as any).google.maps.Map(
      mapRef.current,
      {
        center,
        zoom: 12,
        mapTypeId: "roadmap",
        disableDefaultUI: true,
      }
    );

    // Add click listener to place marker
    mapInstanceRef.current.addListener("click", (e: any) => {
      const pos = e.latLng;
      if (!pos) return;
      const plat = pos.lat().toFixed(6);
      const plng = pos.lng().toFixed(6);
      placeMarker({ lat: parseFloat(plat), lng: parseFloat(plng) });
      setValue("latitude", plat, { shouldValidate: true });
      setValue("longitude", plng, { shouldValidate: true });
    });
  }, [mapReady]);

  // Update marker when lat/lng typed manually
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const nlat = parseFloat(lat as any);
    const nlng = parseFloat(lng as any);
    if (!Number.isNaN(nlat) && !Number.isNaN(nlng)) {
      placeMarker({ lat: nlat, lng: nlng });
      mapInstanceRef.current.setCenter({ lat: nlat, lng: nlng });
    }
  }, [lat, lng]);

  function placeMarker(position: { lat: number; lng: number }) {
    if (!mapInstanceRef.current) return;
    if (markerRef.current) {
      markerRef.current.setPosition(position);
    } else {
      markerRef.current = new (window as any).google.maps.Marker({
        position,
        map: mapInstanceRef.current,
        draggable: true,
        icon: {
          url: "/home/map-marker.png",
          scaledSize: new (window as any).google.maps.Size(30, 40),
        },
      });
      markerRef.current.addListener("dragend", () => {
        const p = markerRef.current!.getPosition();
        if (!p) return;
        const plat = p.lat().toFixed(6);
        const plng = p.lng().toFixed(6);
        setValue("latitude", plat, { shouldValidate: true });
        setValue("longitude", plng, { shouldValidate: true });
      });
    }
  }

  // Geocode locationQuery and center map
  const goToLocation = async () => {
    if (!locationQuery) return;
    try {
      const geocoder = new (window as any).google.maps.Geocoder();
      geocoder.geocode(
        { address: locationQuery },
        (results: any[], status: string) => {
          if (status === "OK" && results.length > 0) {
            const loc = results[0].geometry.location;
            const plat = loc.lat();
            const plng = loc.lng();
            setValue("latitude", plat.toFixed(6), { shouldValidate: true });
            setValue("longitude", plng.toFixed(6), { shouldValidate: true });
            placeMarker({ lat: plat, lng: plng });
            mapInstanceRef.current.setCenter({ lat: plat, lng: plng });
            mapInstanceRef.current.setZoom(15);
          } else {
            alert("Location not found.");
          }
        }
      );
    } catch (err) {
      console.error("Geocode error:", err);
      alert("Failed to find location.");
    }
  };

  async function onSubmit(data: FormData) {
    try {
      const formData = new FormData();
      formData.append("name", data.name);
      formData.append(
        "hasMentalInjury",
        data.hasMentalInjury ? "true" : "false"
      );
      formData.append("latitude", data.latitude);
      formData.append("longitude", data.longitude);
      formData.append("lastSeenClothing", data.lastSeenClothing);

      if (data.imageFile && data.imageFile.length > 0) {
        formData.append("imageFile", data.imageFile[0]);
      }
      window.location.href = `/search_area?lat=${data.latitude}&lng=${data.longitude}`;
    } catch (err) {
      console.error(err);
      alert("Error submitting report");
    }
  }

  return (
    <div className="my-2 min-h-screen flex items-center">
      <Card className="max-w-[800px]  w-4/5 mx-auto">
        <CardHeader>
          <CardTitle>Missing Person / Last Seen Report</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <Label className="mb-1">Name</Label>
              <Input
                {...register("name", { required: "Name is required" })}
                placeholder="Full name"
              />
              {errors.name && (
                <p className="text-sm text-red-600">{errors.name.message}</p>
              )}
            </div>

            <div className="flex items-center space-x-3">
              <Label>Mental injury?</Label>
              <Switch
                checked={!!watch("hasMentalInjury")}
                onCheckedChange={(v) => setValue("hasMentalInjury", Boolean(v))}
              />
            </div>

            <div>
              <Label className="mb-1">Search for a Location</Label>
              <div className="flex gap-2">
                <Input
                  {...register("locationQuery")}
                  placeholder="Type an address or place"
                  onSubmit={goToLocation}
                  onKeyDown={(e) => (e.key === "Enter" ? goToLocation() : null)}
                />
                <Button type="button" onClick={goToLocation}>
                  Go
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">Latitude</Label>
                <Input {...register("latitude")} placeholder="40.7128" />
              </div>
              <div>
                <Label className="mb-1">Longitude</Label>
                <Input {...register("longitude")} placeholder="-74.0060" />
              </div>
            </div>

            {/* New fields */}
            <div>
              <Label className="mb-1">
                Attach an Image of the Missing Person:{" "}
              </Label>
              <Input
                type="file"
                {...register("imageFile")}
                accept="image/png, image/jpg, image/jpeg"
              />
            </div>

            <div>
              <Label className="mb-1">Last Seen Clothing / Description</Label>
              {/* <Textarea
                {...register("lastSeenClothing")}
                placeholder="Describe what the person was last wearing"
              /> */}
            </div>

            <div className="h-64 w-full border rounded-md overflow-hidden">
              <div ref={mapRef} className="h-full w-full" />
            </div>

            <div className="flex justify-end">
              <Button type="submit">Submit report</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
