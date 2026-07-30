"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { useGeographic } from "@/context/GeographicContext";
import { MapPin } from "lucide-react";

interface City {
  id: number;
  name: string;
}

export default function CitySelector() {
  const [cities, setCities] = useState<City[]>([]);
  const { selectedCity, setSelectedCity } = useGeographic();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCities = async () => {
      setLoading(true);
      try {
        const token = Cookies.get("access_token");
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/cities`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (response.ok) {
          const data: City[] = await response.json();
          // Put Jakarta & Malang cities towards the top for easy demo access
          const sorted = [...data].sort((a, b) => {
            const isFeaturedA = a.name.toLowerCase().includes("jakarta") || a.name.toLowerCase().includes("malang");
            const isFeaturedB = b.name.toLowerCase().includes("jakarta") || b.name.toLowerCase().includes("malang");
            if (isFeaturedA && !isFeaturedB) return -1;
            if (!isFeaturedA && isFeaturedB) return 1;
            return a.name.localeCompare(b.name);
          });
          setCities(sorted);
          
          if (sorted.length > 0) {
            const cityExists = sorted.some((c: City) => c.id === selectedCity?.id);
            if (!cityExists) {
              // Prefer Jakarta Selatan or first available
              const defaultFeatured = sorted.find(c => c.name.includes("Jakarta Selatan")) || sorted[0];
              setSelectedCity(defaultFeatured);
            }
          }
        }
      } catch (error) {
        console.error("Failed to fetch cities", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchCities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex items-center gap-2">
      <MapPin className="h-4 w-4 text-muted-foreground" />
      <select
        value={selectedCity?.id || ""}
        onChange={(e) => {
          const cityId = parseInt(e.target.value);
          const city = cities.find((c) => c.id === cityId);
          if (city) {
            setSelectedCity(city);
          }
        }}
        className="bg-transparent text-sm font-medium focus:outline-none border border-input rounded-md px-2 py-1"
        disabled={loading || cities.length === 0}
      >
        {loading ? (
          <option>Loading cities...</option>
        ) : (
          cities.map((city) => (
            <option key={city.id} value={city.id}>
              {city.name}
            </option>
          ))
        )}
      </select>
    </div>
  );
}
