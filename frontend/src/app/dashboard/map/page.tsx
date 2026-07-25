"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { Layers } from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";
import Cookies from "js-cookie";

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
  const { selectedCity } = useGeographic();

  // Fetch facilities
  const { data: facilities = [], isLoading: loadingFacilities } = useQuery({
    queryKey: ['facilities', selectedCity?.id],
    queryFn: async () => {
      const token = Cookies.get("access_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/facilities?city_id=${selectedCity?.id}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to fetch facilities");
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  // Fetch city boundary
  const { data: boundary = null, isLoading: loadingBoundary } = useQuery({
    queryKey: ['boundary', selectedCity?.id],
    queryFn: async () => {
      const token = Cookies.get("access_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/cities/${selectedCity?.id}/boundary`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) {
        if (res.status === 404) return null;
        throw new Error("Failed to fetch boundary");
      }
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  // Fetch city districts
  const { data: districts = null, isLoading: loadingDistricts } = useQuery({
    queryKey: ['districts', selectedCity?.id],
    queryFn: async () => {
      const token = Cookies.get("access_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/cities/${selectedCity?.id}/districts`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to fetch districts");
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  const isLoading = loadingFacilities || loadingBoundary || loadingDistricts;

  // Empty state if no facilities and not loading
  const isEmpty = !isLoading && facilities.length === 0;

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
      
      {isEmpty ? (
        <div className="h-[calc(100vh-12rem)] w-full rounded-xl border shadow-sm flex flex-col items-center justify-center bg-muted/10">
          <Layers className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium">No Data Available</h3>
          <p className="text-muted-foreground mt-2 max-w-md text-center">
            The spatial data for {selectedCity?.name} has not been processed yet. 
            Please run the ETL pipeline for this city.
          </p>
        </div>
      ) : (
        <Map 
          facilities={facilities} 
          boundary={boundary} 
          districts={districts} 
          loading={isLoading} 
        />
      )}
    </div>
  );
}
