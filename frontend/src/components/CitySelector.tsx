"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { useGeographic, City, District } from "@/context/GeographicContext";
import { Layers } from "lucide-react";
import { API_BASE } from "@/lib/api";

export default function CitySelector() {
  const [cities, setCities] = useState<City[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);
  const { selectedCity, setSelectedCity, selectedDistrict, setSelectedDistrict } = useGeographic();
  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);

  // Fetch Cities
  useEffect(() => {
    const fetchCities = async () => {
      setLoadingCities(true);
      try {
        const token = Cookies.get("access_token");
        const response = await fetch(`${API_BASE}/cities`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (response.ok) {
          const data: City[] = await response.json();
          // Sort cities purely alphabetically (A-Z)
          const sorted = [...data].sort((a, b) => a.name.localeCompare(b.name));
          setCities(sorted);

          if (sorted.length > 0) {
            const cityExists = sorted.some((c: City) => c.id === selectedCity?.id);
            if (!cityExists) {
              setSelectedCity(sorted[0]);
            }
          }
        }
      } catch (error) {
        console.error("Failed to fetch cities", error);
      } finally {
        setLoadingCities(false);
      }
    };

    fetchCities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch Districts when selectedCity changes
  useEffect(() => {
    const fetchDistricts = async () => {
      if (!selectedCity?.id) {
        setDistricts([]);
        return;
      }
      setLoadingDistricts(true);
      try {
        const token = Cookies.get("access_token");
        const response = await fetch(`${API_BASE}/cities/${selectedCity.id}/districts`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (response.ok) {
          const data = await response.json();
          if (data && Array.isArray(data.features)) {
            const parsedDistricts: District[] = data.features.map(
              (f: { properties: { id: number; name: string } }) => ({
                id: f.properties.id,
                name: f.properties.name,
              })
            );
            parsedDistricts.sort((a, b) => a.name.localeCompare(b.name));
            setDistricts(parsedDistricts);

            // Verify if currently selected district exists in this city
            if (selectedDistrict) {
              const exists = parsedDistricts.some((d) => d.id === selectedDistrict.id);
              if (!exists) {
                setSelectedDistrict(null);
              }
            }
          } else {
            setDistricts([]);
          }
        }
      } catch (error) {
        console.error("Failed to fetch districts", error);
        setDistricts([]);
      } finally {
        setLoadingDistricts(false);
      }
    };

    fetchDistricts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCity?.id]);

  const selectStyle = {
    backgroundColor: "var(--card)",
    color: "var(--foreground)",
    borderColor: "var(--input)",
  };

  const optionStyle = {
    backgroundColor: "var(--card)",
    color: "var(--foreground)",
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Dropdown Kota */}
      <div className="flex items-center gap-1.5">
        <select
          value={selectedCity?.id || ""}
          onChange={(e) => {
            const cityId = parseInt(e.target.value);
            const city = cities.find((c) => c.id === cityId);
            if (city) {
              setSelectedCity(city);
            }
          }}
          style={selectStyle}
          className="text-xs sm:text-sm font-medium focus:outline-none border rounded-md px-2 py-1 cursor-pointer max-w-[160px] sm:max-w-[200px] truncate"
          disabled={loadingCities || cities.length === 0}
        >
          {loadingCities ? (
            <option style={optionStyle}>Loading cities...</option>
          ) : (
            cities.map((city) => (
              <option key={city.id} value={city.id} style={optionStyle}>
                {city.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Dropdown Kecamatan */}
      <div className="flex items-center gap-1.5">
        <Layers className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <select
          value={selectedDistrict?.id || ""}
          onChange={(e) => {
            const val = e.target.value;
            if (!val) {
              setSelectedDistrict(null);
            } else {
              const districtId = parseInt(val);
              const district = districts.find((d) => d.id === districtId);
              if (district) {
                setSelectedDistrict(district);
              }
            }
          }}
          style={selectStyle}
          className="text-xs sm:text-sm font-medium focus:outline-none border rounded-md px-2 py-1 cursor-pointer max-w-[160px] sm:max-w-[200px] truncate"
          disabled={loadingDistricts || districts.length === 0}
        >
          {loadingDistricts ? (
            <option style={optionStyle}>Loading kecamatan...</option>
          ) : (
            <>
              <option value="" style={optionStyle}>
                Semua Kecamatan ({districts.length})
              </option>
              {districts.map((district) => (
                <option key={district.id} value={district.id} style={optionStyle}>
                  {district.name}
                </option>
              ))}
            </>
          )}
        </select>
      </div>
    </div>
  );
}
