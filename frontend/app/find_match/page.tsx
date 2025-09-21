"use client";

import "./match.css";
import { useEffect, useState } from "react";
import Image from "next/image";
import { OrbitProgress } from "react-loading-indicators";
import { createClient } from "@supabase/supabase-js";
import { Skeleton } from "@/components/ui/skeleton";
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
      <>
        <div className="h-screen flex items-center justify-center">
          <OrbitProgress color="#3391EE" size="medium" />
        </div>
      </>
    );
  return (
    <>
      <div className="p-4">
        <div className="m-2 border-gray-400 border p-2 rounded-lg">
          <div className="text-center">
            <h1 className=" text-3xl">Drone Image Viewer</h1>
            <p className="text-gray-600 max-w-[330px] mb-4 mx-auto">
              As the drone takes more and more images of different entities,
              they will appear here.
            </p>
          </div>
          <h3 className="text-center font-bold">Missing Person Image:</h3>
          <div className="w-full flex justify-center">
            <div className="mx-auto inline-block">
              {submittedImg ? (
                <Image
                  src={submittedImg}
                  height={200}
                  width={200}
                  alt="Submitted"
                  style={{ maxWidth: "100%" }}
                />
              ) : (
                <p>No submitted image found.</p>
              )}
            </div>
          </div>
          <div className="text-center mt-4 ">
            <h3 className="font-bold text-2xl">
              Below Are Entities the Drone Took Pictures of
            </h3>
            <p className="text-sm">
              Green borders = Gemini thinks the target has been found!
            </p>
            <div className="flex items-center justify-center flex-col">
              <div className="flex flex-row flex-wrap gap-2">
                {droneImages.length === 0 ? (
                  <Skeleton className="h-[150px] bg-black/80 w-[150px] rounded-lg" />
                ) : (
                  droneImages.map((img, idx) => (
                    <img
                      key={img.src}
                      src={img.src}
                      alt={`Drone image ${idx}`}
                      style={{
                        border:
                          img.isMatch === 1
                            ? "3px solid green"
                            : img.isMatch === 2
                            ? "3px solid red"
                            : "none",
                        maxWidth: "150px",
                      }}
                    />
                  ))
                )}
              </div>
              <div></div>
              <ul>
                {seenTimestamps.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default HomePage;
