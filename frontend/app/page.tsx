"use client";
import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "../lib/utils";
import { format } from "date-fns";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";

type FormData = {
  name: string;
  hasMentalInjury: boolean;
  age: number | "";
  missingDuration: string;
  latitude: string;
  longitude: string;
};

export default function MissingPersonForm() {
  const [date, setDate] = useState<Date>();
  const [dateError, setDateError] = useState<string | null>(null);

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
      age: "",
      missingDuration: "",
      latitude: "",
      longitude: "",
    },
  });

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any | null>(null);
  const markerRef = useRef<any | null>(null);
  const autocompleteRef = useRef<any | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const lat = watch("latitude");
  const lng = watch("longitude");

  // Load Google Maps script with places library
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_MAPS_API;
    if (!key) {
      console.warn("Missing NEXT_PUBLIC_MAPS_API. Map won't load.");
      return;
    }

    if ((window as any).google?.maps) {
      setMapReady(true);
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => setMapReady(true);
    document.head.appendChild(script);
  }, []);

  // Initialize map and autocomplete
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

    // Click to place marker
    mapInstanceRef.current.addListener("click", (e: any) => {
      const pos = e.latLng;
      if (!pos) return;
      const plat = pos.lat().toFixed(6);
      const plng = pos.lng().toFixed(6);
      placeMarker({ lat: parseFloat(plat), lng: parseFloat(plng) });
      setValue("latitude", plat, { shouldValidate: true });
      setValue("longitude", plng, { shouldValidate: true });
    });

    // Autocomplete
    const input = document.getElementById("autocomplete") as HTMLInputElement;
    if (input) {
      autocompleteRef.current = new (
        window as any
      ).google.maps.places.Autocomplete(input);
      autocompleteRef.current.bindTo("bounds", mapInstanceRef.current);
      autocompleteRef.current.addListener("place_changed", () => {
        const place = autocompleteRef.current.getPlace();
        if (!place.geometry || !place.geometry.location) return;

        const location = place.geometry.location;
        const plat = location.lat().toFixed(6);
        const plng = location.lng().toFixed(6);
        mapInstanceRef.current.setCenter(location);
        mapInstanceRef.current.setZoom(15);
        placeMarker({ lat: parseFloat(plat), lng: parseFloat(plng) });
        setValue("latitude", plat, { shouldValidate: true });
        setValue("longitude", plng, { shouldValidate: true });
      });
    }
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

  function onSubmit(data: FormData) {
    console.log("submit payload:", {
      ...data,
      latitude: parseFloat(data.latitude),
      longitude: parseFloat(data.longitude),
    });
    alert("Submitted — check console for payload.");
  }

  return (
    <div className="h-screen flex items-center">
      <Card className="max-w-3xl mx-auto">
        <CardHeader>
          <CardTitle>Missing Person / Last Seen Report</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <Label>Name</Label>
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
              <Label>Search for a Location</Label>
              <Input id="autocomplete" placeholder="Type an address or place" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Latitude</Label>
                <Input
                  {...register("latitude", {
                    pattern: {
                      value: /^-?\d+(\.\d+)?$/,
                      message: "Invalid latitude",
                    },
                  })}
                  placeholder="40.7128"
                />
              </div>
              <div>
                <Label>Longitude</Label>
                <Input
                  {...register("longitude", {
                    pattern: {
                      value: /^-?\d+(\.\d+)?$/,
                      message: "Invalid longitude",
                    },
                  })}
                  placeholder="-74.0060"
                />
              </div>
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
