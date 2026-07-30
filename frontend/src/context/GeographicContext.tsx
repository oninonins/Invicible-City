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

// Default city — dipakai langsung di initial state agar tidak ada flash kosong
const DEFAULT_CITY = { id: 264, name: "Kota Adm. Jakarta Selatan" };

export function GeographicProvider({ children }: { children: React.ReactNode }) {
  const [selectedCity, setSelectedCityState] = useState<City | null>(DEFAULT_CITY);

  useEffect(() => {
    // Sinkronisasi dengan localStorage setelah mount — tidak memblokir render
    try {
      const storedCity = localStorage.getItem("sdgs_selected_city");
      if (storedCity) {
        setSelectedCityState(JSON.parse(storedCity));
      } else {
        localStorage.setItem("sdgs_selected_city", JSON.stringify(DEFAULT_CITY));
      }
    } catch (e) {
      console.error("Failed to read stored city", e);
    }
  }, []);

  const setSelectedCity = (city: City) => {
    setSelectedCityState(city);
    localStorage.setItem("sdgs_selected_city", JSON.stringify(city));
  };

  return (
    <GeographicContext.Provider value={{ selectedCity, setSelectedCity }}>
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
