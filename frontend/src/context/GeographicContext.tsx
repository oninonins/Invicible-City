"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export interface City {
  id: number;
  name: string;
}

export interface District {
  id: number;
  name: string;
}

interface GeographicContextType {
  selectedCity: City | null;
  setSelectedCity: (city: City) => void;
  selectedDistrict: District | null;
  setSelectedDistrict: (district: District | null) => void;
}

const GeographicContext = createContext<GeographicContextType | undefined>(undefined);

export function GeographicProvider({ children }: { children: React.ReactNode }) {
  const [selectedCity, setSelectedCityState] = useState<City | null>(null);
  const [selectedDistrict, setSelectedDistrictState] = useState<District | null>(null);

  useEffect(() => {
    // Sinkronisasi dengan localStorage setelah mount — tidak memblokir render
    try {
      const storedCity = localStorage.getItem("sdgs_selected_city");
      if (storedCity) {
        setSelectedCityState(JSON.parse(storedCity));
      }

      const storedDistrict = localStorage.getItem("sdgs_selected_district");
      if (storedDistrict) {
        setSelectedDistrictState(JSON.parse(storedDistrict));
      }
    } catch (e) {
      console.error("Failed to read stored geographic context", e);
    }
  }, []);

  const setSelectedCity = (city: City) => {
    setSelectedCityState(city);
    localStorage.setItem("sdgs_selected_city", JSON.stringify(city));
    // Reset district when city changes
    setSelectedDistrictState(null);
    localStorage.removeItem("sdgs_selected_district");
  };

  const setSelectedDistrict = (district: District | null) => {
    setSelectedDistrictState(district);
    if (district) {
      localStorage.setItem("sdgs_selected_district", JSON.stringify(district));
    } else {
      localStorage.removeItem("sdgs_selected_district");
    }
  };

  return (
    <GeographicContext.Provider value={{ selectedCity, setSelectedCity, selectedDistrict, setSelectedDistrict }}>
      {children}
    </GeographicContext.Provider>
  );
}

export function useGeographic() {
  const context = useContext(GeographicContext);
  if (context === undefined) {
    throw new Error("useGeographic must be used within a GeographicProvider");
  }
  return context;
}
