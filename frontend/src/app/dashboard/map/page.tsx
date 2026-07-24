"use client";

import dynamic from "next/dynamic";
import { Layers } from "lucide-react";

// Dynamically import Map component to avoid SSR issues with Leaflet
const Map = dynamic(() => import("@/components/map/Map"), { 
  ssr: false,
  loading: () => (
    <div className="h-[calc(100vh-12rem)] w-full rounded-xl border shadow-sm flex items-center justify-center bg-muted/20">
      <div className="flex flex-col items-center text-muted-foreground">
        <Layers className="h-8 w-8 mb-2 animate-pulse" />
        <p>Loading Map...</p>
      </div>
    </div>
  )
});

export default function MapPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Interactive Map</h1>
          <p className="text-muted-foreground">
            Explore public facilities and urban fairness distribution.
          </p>
        </div>
      </div>
      
      <Map />
    </div>
  );
}
