"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Cookies from "js-cookie";
import { useGeographic, City, District } from "@/context/GeographicContext";
import { Layers, Search, ChevronDown, Check } from "lucide-react";
import { API_BASE } from "@/lib/api";

export default function CitySelector() {
  const [cities, setCities] = useState<City[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);
  const { selectedCity, setSelectedCity, selectedDistrict, setSelectedDistrict } = useGeographic();
  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);

  // Search & Combobox states
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listboxRef = useRef<HTMLUListElement>(null);

  // Fetch Cities
  useEffect(() => {
    const fetchCities = async () => {
      setLoadingCities(true);
      try {
        const token = Cookies.get("access_token");
        const response = await fetch(`${API_BASE}/cities/`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (response.ok) {
          const data: City[] = await response.json();
          // Sort cities alphabetically (A-Z)
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

  // Filter cities locally
  const filteredCities = cities.filter((city) =>
    city.name.toLowerCase().includes(searchQuery.trim().toLowerCase())
  );

  // Close dropdown and clear search
  const handleClose = useCallback(() => {
    setIsOpen(false);
    setSearchQuery("");
    setHighlightedIndex(0);
  }, []);

  // Select a city
  const handleSelectCity = useCallback(
    (city: City) => {
      setSelectedCity(city);
      handleClose();
    },
    [setSelectedCity, handleClose]
  );

  // Auto-focus search input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);

      // Set initial highlighted index to current selected city if in results
      if (selectedCity) {
        const idx = filteredCities.findIndex((c) => c.id === selectedCity.id);
        if (idx !== -1) {
          setHighlightedIndex(idx);
        } else {
          setHighlightedIndex(0);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listboxRef.current) {
      const activeElement = listboxRef.current.children[highlightedIndex] as HTMLElement | undefined;
      if (activeElement) {
        activeElement.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex, isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        handleClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, handleClose]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < filteredCities.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : filteredCities.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredCities[highlightedIndex]) {
        handleSelectCity(filteredCities[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleClose();
    } else if (e.key === "Tab") {
      handleClose();
    }
  };

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
      {/* Searchable Combobox Kota */}
      <div className="relative" ref={containerRef}>
        {/* Trigger Button */}
        <button
          type="button"
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-controls="city-listbox"
          aria-label="Pilih Kota atau Kabupaten"
          onClick={() => {
            if (!loadingCities && cities.length > 0) {
              setIsOpen((prev) => !prev);
            }
          }}
          onKeyDown={handleKeyDown}
          style={selectStyle}
          disabled={loadingCities || cities.length === 0}
          className="text-xs sm:text-sm font-medium focus:outline-none focus:ring-1 focus:ring-primary border rounded-md px-2.5 py-1 cursor-pointer max-w-[170px] sm:max-w-[210px] flex items-center justify-between gap-1.5 transition-colors hover:bg-muted/40 shadow-sm"
        >
          <span className="truncate text-left">
            {loadingCities ? "Loading cities..." : selectedCity?.name || "Pilih Kota"}
          </span>
          <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
        </button>

        {/* Dropdown Popover */}
        {isOpen && (
          <div className="absolute left-0 top-full mt-1.5 w-64 sm:w-72 bg-card border border-border rounded-lg shadow-xl z-50 flex flex-col overflow-hidden animate-in fade-in-0 zoom-in-95 duration-100">
            {/* Search Input Box */}
            <div className="p-2 border-b border-border bg-muted/20 flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setHighlightedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Cari kota atau kabupaten..."
                className="bg-transparent text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none w-full"
              />
            </div>

            {/* City Options List */}
            <ul
              id="city-listbox"
              role="listbox"
              ref={listboxRef}
              className="max-h-60 overflow-y-auto py-1 divide-y divide-border/20 text-xs sm:text-sm"
            >
              {filteredCities.length > 0 ? (
                filteredCities.map((city, idx) => {
                  const isSelected = city.id === selectedCity?.id;
                  const isHighlighted = idx === highlightedIndex;

                  return (
                    <li
                      key={city.id}
                      id={`city-option-${city.id}`}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => handleSelectCity(city)}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                      className={`px-3 py-2 text-left cursor-pointer transition-colors flex items-center justify-between gap-2 ${
                        isHighlighted
                          ? "bg-primary/10 text-primary font-medium"
                          : isSelected
                          ? "bg-muted/60 text-foreground font-semibold"
                          : "text-foreground hover:bg-muted/40"
                      }`}
                    >
                      <span className="truncate">{city.name}</span>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                      )}
                    </li>
                  );
                })
              ) : (
                <li className="px-3 py-4 text-center text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">Tidak ditemukan</p>
                  <p className="leading-relaxed">
                    Tidak ada kota atau kabupaten yang cocok dengan &quot;{searchQuery}&quot;.
                  </p>
                </li>
              )}
            </ul>
          </div>
        )}
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
          className="text-xs sm:text-sm font-medium focus:outline-none border rounded-md px-2 py-1 cursor-pointer max-w-[160px] sm:max-w-[200px] truncate shadow-sm"
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
