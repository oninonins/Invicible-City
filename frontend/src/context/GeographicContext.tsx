"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface City {
  id: number;
  name: string;
}

interface GeographicContextType {
  selectedCity: City | null;
  setSelectedCity: (city: City) => void;
}

const GeographicContext = createContext<GeographicContextType | undefined>(undefined);

export function GeographicProvider({ children }: { children: React.ReactNode }) {
  const [selectedCity, setSelectedCityState] = useState<City | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const storedCity = localStorage.getItem("sdgs_selected_city");
    if (storedCity) {
      try {
        setSelectedCityState(JSON.parse(storedCity));
      } catch (e) {
        console.error("Failed to parse stored city", e);
      }
    } else {
      // Default city if none selected
      const defaultCity = { id: 3573, name: "Malang" };
      setSelectedCityState(defaultCity);
      localStorage.setItem("sdgs_selected_city", JSON.stringify(defaultCity));
    }
  }, []);

  const setSelectedCity = (city: City) => {
    setSelectedCityState(city);
    localStorage.setItem("sdgs_selected_city", JSON.stringify(city));
  };

  // Provide a safe default context even before mount to prevent hydration hook errors
  const value = { selectedCity, setSelectedCity };

  return (
    <GeographicContext.Provider value={value}>
      <div style={{ visibility: isMounted ? 'visible' : 'hidden' }}>
        {children}
      </div>
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
