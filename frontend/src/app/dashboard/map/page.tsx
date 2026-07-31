"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { 
  Layers, 
  Building2, 
  School as SchoolIcon, 
  Hospital as HospitalIcon, 
  Stethoscope, 
  Bus as BusIcon, 
  Trees as ParkIcon,
  MapPin,
  AlertTriangle,
  X
} from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";
import Cookies from "js-cookie";
import { Facility } from "@/components/map/Map";
import { API_BASE } from "@/lib/api";

// Dynamic import untuk Leaflet Map
const Map = dynamic(() => import("@/components/map/Map"), { 
  ssr: false,
  loading: () => (
    <div className="h-[calc(100vh-10rem)] w-full rounded-xl border border-border shadow-sm flex flex-col items-center justify-center bg-muted/20">
      <Layers className="h-8 w-8 mb-2 text-muted-foreground animate-pulse" />
      <p className="text-xs font-medium text-muted-foreground">Memuat Engine & Layer Spasial...</p>
    </div>
  )
});

const CATEGORIES = [
  { id: "ALL", label: "Semua Fasilitas", icon: Building2, color: "bg-slate-800 text-white" },
  { id: "School", label: "Sekolah", icon: SchoolIcon, color: "bg-blue-600 text-white" },
  { id: "Hospital", label: "Rumah Sakit", icon: HospitalIcon, color: "bg-red-600 text-white" },
  { id: "Clinic", label: "Klinik", icon: Stethoscope, color: "bg-rose-600 text-white" },
  { id: "BusStop", label: "Halte Bus", icon: BusIcon, color: "bg-amber-600 text-white" },
  { id: "Park", label: "Taman", icon: ParkIcon, color: "bg-emerald-600 text-white" },
];

export default function MapPage() {
  const { selectedCity, selectedDistrict } = useGeographic();
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);

  // Ambil fasilitas
  const { data: facilities = [], isLoading: loadingFacilities, isError: facilitiesError } = useQuery<Facility[]>({
    queryKey: ['facilities', selectedCity?.id, selectedDistrict?.id],
    queryFn: async () => {
      if (!selectedCity?.id) return [];
      const token = Cookies.get("access_token");
      const districtParam = selectedDistrict?.id ? `&district_id=${selectedDistrict.id}` : '';
      const res = await fetch(`${API_BASE}/facilities?city_id=${selectedCity.id}${districtParam}&limit=500`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error("Gagal mengambil data fasilitas");
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  // Ambil batas kota
  const { data: boundary = null, isLoading: loadingBoundary } = useQuery({
    queryKey: ['boundary', selectedCity?.id],
    queryFn: async () => {
      if (!selectedCity?.id) return null;
      const token = Cookies.get("access_token");
      const res = await fetch(`${API_BASE}/cities/${selectedCity.id}/boundary`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  // Ambil kecamatan kota
  const { data: districts = null, isLoading: loadingDistricts } = useQuery({
    queryKey: ['districts', selectedCity?.id],
    queryFn: async () => {
      if (!selectedCity?.id) return null;
      const token = Cookies.get("access_token");
      const res = await fetch(`${API_BASE}/cities/${selectedCity.id}/districts`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  const isLoading = loadingFacilities || loadingBoundary || loadingDistricts;
  const isEmpty = !isLoading && !facilitiesError && facilities.length === 0;

  // Hitung jumlah per kategori
  const schoolCount = facilities.filter(f => f.facility_type === 'School').length;
  const hospitalCount = facilities.filter(f => f.facility_type === 'Hospital').length;
  const clinicCount = facilities.filter(f => f.facility_type === 'Clinic').length;
  const busStopCount = facilities.filter(f => f.facility_type === 'BusStop').length;
  const parkCount = facilities.filter(f => f.facility_type === 'Park').length;

  return (
    <div className="space-y-4 h-[calc(100vh-6rem)] flex flex-col">
      {/* Bar Kontrol Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-card border border-border p-3 rounded-xl shadow-sm">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
            <span>Peta Spasial Interaktif</span>
            <span className="text-xs font-mono font-medium text-muted-foreground">
              ({selectedCity?.name}{selectedDistrict ? ` • ${selectedDistrict.name}` : ''})
            </span>
          </h1>
        </div>

        {/* Toggle Filter 5 Kategori */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;

            let count = facilities.length;
            if (cat.id === "School") count = schoolCount;
            if (cat.id === "Hospital") count = hospitalCount;
            if (cat.id === "Clinic") count = clinicCount;
            if (cat.id === "Bus Stop") count = busStopCount;
            if (cat.id === "Park") count = parkCount;

            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                  isActive 
                    ? `${cat.color} shadow-sm font-semibold` 
                    : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{cat.label}</span>
                <span className={`px-1.5 py-0.2 text-[10px] rounded-full font-mono ${
                  isActive ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      
      {/* Kanvas Utama Peta */}
      <div className="flex-1 w-full rounded-xl overflow-hidden relative">
        {facilitiesError ? (
          <div className="h-full w-full rounded-xl border border-border bg-card p-8 flex flex-col items-center justify-center text-center shadow-sm">
            <AlertTriangle className="h-12 w-12 text-red-500 mb-3" />
            <h3 className="text-lg font-bold text-foreground">Gagal Memuat Fasilitas</h3>
            <p className="text-sm text-muted-foreground max-w-md mt-1">
              Data fasilitas untuk <strong className="text-foreground">{selectedCity?.name}</strong> gagal dimuat. Coba muat ulang halaman atau pilih kota lain.
            </p>
          </div>
        ) : isEmpty ? (
          <div className="h-full w-full rounded-xl border border-border bg-card p-8 flex flex-col items-center justify-center text-center shadow-sm">
            <MapPin className="h-12 w-12 text-muted-foreground mb-3" />
            <h3 className="text-lg font-bold text-foreground">Tidak Ada Data Spasial</h3>
            <p className="text-sm text-muted-foreground max-w-md mt-1">
              Data fasilitas dan batas wilayah untuk <strong className="text-foreground">{selectedCity?.name}</strong> belum di-import ke database spasial.
            </p>
          </div>
        ) : (
          <Map 
            facilities={facilities} 
            boundary={boundary} 
            districts={districts} 
            loading={isLoading}
            activeFilter={activeCategory}
            onSelectFacility={(fac) => setSelectedFacility(fac)}
          />
        )}

        {/* Drawer Detail Penanda Yang Dipilih */}
        {selectedFacility && (
          <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-[1000] bg-card border border-border p-4 rounded-xl shadow-lg animate-in slide-in-from-bottom-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-foreground">{selectedFacility.name}</h4>
                  <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                    {selectedFacility.facility_type}
                  </span>
                </div>
              </div>
              <button 
                onClick={() => setSelectedFacility(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-3 pt-3 border-t border-border grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground block text-[10px]">Lintang (Latitude)</span>
                <span className="font-mono text-foreground">{selectedFacility.lat.toFixed(5)}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px]">Bujur (Longitude)</span>
                <span className="font-mono text-foreground">{selectedFacility.lng.toFixed(5)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
