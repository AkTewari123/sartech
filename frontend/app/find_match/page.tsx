"use client";

import "./match.css";
import { useEffect, useState } from "react";
import Image from "next/image";
import { OrbitProgress } from "react-loading-indicators";
import { createClient } from "@supabase/supabase-js";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const BASE_BUCKET = "base_comparison";
const DRONE_BUCKET = "pi-image";

const HomePage: React.FC = () => {
  function parseAndFormatTimestamp(ts: string): string | null {
    const match = ts.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
    if (!match) return null;

    const [_, year, month, day, hour, minute, second] = match.map(Number);

    const date = new Date(year, month - 1, day, hour, minute, second);

    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    const getOrdinal = (n: number) => {
      if (n > 3 && n < 21) return "th";
      switch (n % 10) {
        case 1:
          return "st";
        case 2:
          return "nd";
        case 3:
          return "rd";
        default:
          return "th";
      }
    };

    const formatted = `${
      monthNames[date.getMonth()]
    } ${date.getDate()}${getOrdinal(
      date.getDate()
    )}, ${date.getFullYear()} at ${date.getHours()}:${String(
      date.getMinutes()
    ).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
    return formatted;
  }
  const [submittedImg, setSubmittedImg] = useState<string | null>(null);
  const [droneImages, setDroneImages] = useState<
    { src: string; isMatch: number | null }[]
  >([]);

  // Helper to convert an image URL to base64
  const urlToBase64 = async (url: string) => {
    const res = await fetch(url);
    const blob = await res.blob();
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };
  const [seenTimestamps, setTimeStamps] = useState([]);
  useEffect(() => {
    const last8 = window.location.href.slice(-8);

    // Check submitted image (png or jpg)
    const tryExtensions = async () => {
      const exts = ["png", "jpg"];
      for (const ext of exts) {
        const url = `${SUPABASE_URL}/storage/v1/object/public/${BASE_BUCKET}/${last8}.${ext}`;
        try {
          const res = await fetch(url, { method: "HEAD" });
          if (res.ok) {
            setSubmittedImg(url);
            return;
          }
        } catch {}
      }
      setSubmittedImg(null);
    };
    tryExtensions();

    // Poll drone images every 5 seconds for 20 seconds
    let elapsed = 0;
    const interval = setInterval(async () => {
      elapsed += 5;
      try {
        const { data: files, error } = await supabase.storage
          .from(DRONE_BUCKET)
          .list("", { limit: 100 });

        if (!error && files) {
          const filtered = files
            .filter((f: any) => f.name.startsWith(last8))
            .map((f: any) => ({
              src: `${SUPABASE_URL}/storage/v1/object/public/${DRONE_BUCKET}/${f.name}`,
              isMatch: 0,
            }));
          if (filtered.length > droneImages.length) setDroneImages(filtered);

          // Compare each drone image to the submitted image via Gemini
          if (submittedImg) {
            const submittedBase64 = await urlToBase64(submittedImg);

            const updated = await Promise.all(
              filtered.map(async (img) => {
                try {
                  const droneBase64 = await urlToBase64(img.src);

                  const res = await fetch(
                    "http://127.0.0.1:5500/check_similarity",
                    {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        image1: submittedBase64,
                        image2: droneBase64,
                      }),
                    }
                  );
                  const data = await res.json();
                  if (data.result?.toLowerCase().startsWith("yes")) {
                    console.log(
                      img.src.split("/").pop()!.split("-")[1].split(".")[0]
                    );
                    const msg = `Suspect has been seen at ${
                      parseAndFormatTimestamp(
                        img.src.split("/").pop()!.split("-")[1].split(".")[0]
                      ) || "a recent time!"
                    }`;
                    setTimeStamps((prev: any) => {
                      if (prev.includes(msg)) {
                        return prev;
                      } else {
                        prev.push(msg);
                        return prev;
                      }
                    });
                  }
                  return {
                    ...img,
                    isMatch: data.result?.toLowerCase().startsWith("yes")
                      ? 1
                      : 2,
                  };
                } catch (err) {
                  console.error(err);
                  return { ...img, isMatch: 2 };
                }
              })
            );
            if (updated.length > droneImages.length) setDroneImages(updated);
          }
        }
      } catch (err) {
        console.error(err);
      }

      if (elapsed >= 20) clearInterval(interval);
    }, 5000);

    return () => clearInterval(interval);
  }, [submittedImg]);
  if (submittedImg === null)
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <Card className="backdrop-blur-sm bg-white/90 shadow-xl border-0 p-8">
          <CardContent className="flex flex-col items-center space-y-6">
            <OrbitProgress color="#3391EE" size="medium" />
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold text-gray-800">Initializing Search</h2>
              <p className="text-gray-600">Loading missing person data and connecting to drone network...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <Card className="backdrop-blur-sm bg-white/90 shadow-xl border-0">
          <CardHeader className="text-center space-y-4">
            <CardTitle className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Real-Time Drone Surveillance
            </CardTitle>
            <CardDescription className="text-lg text-gray-600 max-w-2xl mx-auto">
              Monitor live drone feeds and AI-powered facial recognition to locate missing persons in real-time
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Missing Person Section */}
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
              <CardHeader>
                <CardTitle className="text-xl text-center text-blue-800">
                  Missing Person Profile
                </CardTitle>
              </CardHeader>
              <CardContent className="flex justify-center">
                <div className="relative">
                  {submittedImg ? (
                    <div className="relative group">
                      <Image
                        src={submittedImg}
                        height={250}
                        width={250}
                        alt="Missing Person"
                        className="rounded-xl shadow-lg object-cover border-4 border-blue-200 transition-transform group-hover:scale-105"
                        style={{ aspectRatio: "1/1" }}
                      />
                      <div className="absolute inset-0 rounded-xl bg-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  ) : (
                    <div className="w-[250px] h-[250px] bg-gray-200 rounded-xl flex items-center justify-center">
                      <p className="text-gray-500">No image available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Drone Surveillance Section */}
            <Card className="bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
              <CardHeader>
                <CardTitle className="text-xl text-center text-purple-800">
                  Live Drone Feed Analysis
                </CardTitle>
                <CardDescription className="text-center text-purple-600">
                  <Badge variant="success" className="mr-2">LIVE</Badge>
                  AI analyzing drone footage for potential matches
                </CardDescription>
              </CardHeader>
              
              <CardContent>
                <div className="flex justify-center">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-4xl">
                  {droneImages.length === 0 ? (
                    Array.from({ length: 8 }).map((_, idx) => (
                      <div key={idx} className="relative">
                        <Skeleton className="h-[150px] w-full rounded-lg bg-gradient-to-br from-gray-200 to-gray-300" />
                        <div className="absolute bottom-2 right-2">
                          <Badge variant="secondary" className="text-xs">
                            Loading...
                          </Badge>
                        </div>
                      </div>
                    ))
                  ) : (
                    droneImages.map((img, idx) => (
                      <div key={img.src} className="relative group">
                        <div className="relative overflow-hidden rounded-lg">
                          <img
                            src={img.src}
                            alt={`Drone capture ${idx + 1}`}
                            className="w-full h-[150px] object-cover transition-all duration-300 group-hover:scale-110"
                          />
                          {img.isMatch === 1 && (
                            <div className="absolute inset-0 bg-green-500/30 border-4 border-green-500 rounded-lg animate-pulse" />
                          )}
                          {img.isMatch === 2 && (
                            <div className="absolute inset-0 bg-red-500/10 border-2 border-red-300 rounded-lg" />
                          )}
                        </div>
                        
                        {/* Status Badge */}
                        <div className="absolute top-2 right-2">
                          {img.isMatch === 1 && (
                            <Badge variant="success" className="shadow-lg">
                              MATCH!
                            </Badge>
                          )}
                          {img.isMatch === 2 && (
                            <Badge variant="secondary" className="shadow-lg">
                              No Match
                            </Badge>
                          )}
                          {img.isMatch === null && (
                            <Badge variant="warning" className="shadow-lg">
                              Analyzing...
                            </Badge>
                          )}
                        </div>
                        
                        {/* Image number */}
                        <div className="absolute bottom-2 left-2">
                          <Badge variant="outline" className="bg-black/50 text-white border-white/20">
                            #{idx + 1}
                          </Badge>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
              </CardContent>
            </Card>

            {/* Detection Results Section */}
            {seenTimestamps.length > 0 && (
              <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
                <CardHeader>
                  <CardTitle className="text-xl text-center text-green-800 flex items-center justify-center gap-2">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    Detection Results
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {seenTimestamps.map((timestamp, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-3 p-3 bg-white/60 rounded-lg border border-green-200"
                      >
                        <Badge variant="success">DETECTED</Badge>
                        <p className="text-green-800 font-medium">{timestamp}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default HomePage;
