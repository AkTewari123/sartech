import { NextResponse } from "next/server";

// Example static flight path coordinates (replace with DB or live data)
const flightPathCoordinates = [
  { lat: 40.742, lng: -74.177 },
  { lat: 40.745, lng: -74.18 },
  { lat: 40.748, lng: -74.175 },
  { lat: 40.75, lng: -74.17 },
];

export async function GET() {
  return NextResponse.json({
    path: flightPathCoordinates,
    updatedAt: new Date().toISOString(),
  });
}
