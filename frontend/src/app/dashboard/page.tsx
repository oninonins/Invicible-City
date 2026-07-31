"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Cookies from "js-cookie";
import {
  Building2,
  School as SchoolIcon,
  Hospital as HospitalIcon,
  Stethoscope,
  Bus as BusIcon,
  Trees as ParkIcon,
  Layers,
  MapPin
} from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";
import { Facility } from "@/components/map/Map";
import { API_BASE } from "@/lib/api";

// Import Leaflet Map secara dinamis untuk menghindari SSR error
const Map = dynamic(() => import("@/components/map/Map"), {
  ssr: false,
  loading: () => (
    <div className="h-[520px] w-full rounded-xl border border-border flex flex-col items-center justify-center bg-muted/20">
      <Layers className="h-8 w-8 text-muted-foreground animate-pulse mb-2" />
      <p className="text-xs font-medium text-muted-foreground">Memuat Engine Map Spasial...</p>
    </div>
  )
});

interface AnalyticsData {
  overall_score: number;
  total_facilities: number;
  breakdown: Record<string, number>;
  status: string;
}

const CATEGORIES = [
  { id: "ALL", label: "Semua Kategori", icon: Building2, color: "bg-slate-800 text-white" },
  { id: "School", label: "Sekolah", icon: SchoolIcon, color: "bg-blue-600 text-white" },
  { id: "Hospital", label: "Rumah Sakit", icon: HospitalIcon, color: "bg-red-600 text-white" },
  { id: "Clinic", label: "Klinik", icon: Stethoscope, color: "bg-rose-600 text-white" },
  { id: "BusStop", label: "Halte Bus", icon: BusIcon, color: "bg-amber-600 text-white" },
  { id: "Park", label: "Taman", icon: ParkIcon, color: "bg-emerald-600 text-white" },
];

export default function DashboardPage() {
  const { selectedCity, selectedDistrict } = useGeographic();
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);

  // Ambil data analitik UFS
  const { data: analytics, isLoading: loadingAnalytics } = useQuery<AnalyticsData>({
    queryKey: ['analytics', selectedCity?.id],
    queryFn: async () => {
      if (!selectedCity?.id) return null;
      const token = Cookies.get("access_token");
      const res = await fetch(`${API_BASE}/analytics/ufs?city_id=${selectedCity.id}`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error("Gagal mengambil data analitik");
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  // Ambil data Fasilitas
  const { data: facilities = [], isLoading: loadingFacilities } = useQuery<Facility[]>({
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

  // Ambil GeoJSON Batas Kota
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

  // Ambil GeoJSON Kecamatan
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

  const isLoadingAnalytics = loadingAnalytics;
  const isLoadingMap = loadingFacilities; // Map tampil independen dari analytics
  const isLoading = loadingAnalytics || loadingFacilities || loadingBoundary || loadingDistricts;
  const hasNoData = !isLoading && facilities.length === 0;

  // Hitung jumlah per kategori
  const schoolCount = facilities.filter(f => f.facility_type === 'School').length;
  const hospitalCount = facilities.filter(f => f.facility_type === 'Hospital').length;
  const clinicCount = facilities.filter(f => f.facility_type === 'Clinic').length;
  const busStopCount = facilities.filter(f => f.facility_type === 'BusStop').length;
  const parkCount = facilities.filter(f => f.facility_type === 'Park').length;

  const score = analytics?.overall_score ?? 0;
  const rawStatus = analytics?.status ?? "";
  const statusStr = rawStatus === "Good" ? "Baik" : rawStatus === "Fair" ? "Cukup" : rawStatus === "Poor" ? "Kurang" : (facilities.length > 0 ? "Terhitung" : "Tidak Ada Data");

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header & Konteks Kota */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {selectedCity?.name || "Pilih Kota"}
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Analisis keadilan spasial 15 menit & kesenjangan aksesibilitas layanan publik.
          </p>
        </div>

        {/* Card Badge Skor Keadilan Perkotaan */}
        <div className="flex items-center gap-4 bg-card border border-border rounded-xl p-3 shadow-sm">
          <div className="flex flex-col items-end">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Urban fairness score</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-foreground tracking-tight">
                {isLoadingAnalytics ? "..." : (score > 0 ? `${score}/100` : "N/A")}
              </span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${statusStr === "Baik" ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20" :
                  statusStr === "Cukup" ? "bg-amber-500/10 text-amber-600 border border-amber-500/20" :
                    "bg-slate-500/10 text-slate-600 border border-slate-500/20"
                }`}>
                {statusStr}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Card Wawasan Utama */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Penilaian Spasial */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="mb-2">
              <span className="text-xs font-bold text-primary uppercase tracking-wider">Penilaian Spasial</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground">Kota Yang Dianalisis</h3>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              Mengevaluasi batas administratif dan sebaran fasilitas di <strong className="text-foreground">{selectedCity?.name}</strong>.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-border/60 text-xs font-medium text-muted-foreground">
            Total Titik Terpeta: <strong className="text-foreground">{facilities.length}</strong>
          </div>
        </div>

        {/* Card 2: Indeks Keadilan */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="mb-2">
              <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Indeks Keadilan</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground">Rating UFS: {statusStr}</h3>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {score >= 70 ? "Cakupan layanan publik merata di berbagai kecamatan." :
                score >= 40 ? "Distribusi cukup merata dengan beberapa titik kesenjangan akses." :
                  "Terdapat variasi kesenjangan akses antar kecamatan."}
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-border/60 text-xs font-medium text-muted-foreground">
            Target Acuan: <strong className="text-foreground">20 fasilitas / kecamatan</strong>
          </div>
        </div>

        {/* Card 3: Kesenjangan Kritis */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="mb-2">
              <span className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">Kesenjangan Kritis</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground">Defisit Layanan Terdeteksi</h3>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {hospitalCount + clinicCount < 5
                ? "Defisit fasilitas kesehatan terdeteksi di sektor pemukiman."
                : "Akses halte bus & transportasi perlu diperluas di kecamatan luar."}
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-border/60 text-xs font-medium text-muted-foreground">
            Rasio Kesehatan vs Transportasi: <strong className="text-foreground">{hospitalCount + clinicCount} : {busStopCount}</strong>
          </div>
        </div>

        {/* Card 4: Rekomendasi Kebijakan */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="mb-2">
              <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">Rekomendasi Kebijakan</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground">Prioritas Optimasi</h3>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              Prioritaskan penambahan puskesmas pembantu & halte pengumpan di kecamatan ber-skor UFS rendah.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-border/60 text-xs font-medium text-muted-foreground">
            Status: <strong className="text-foreground">Wawasan berbasis data</strong>
          </div>
        </div>
      </div>

      {/* Peta Interaktif & Bar Filter Kategori */}
      <div className="space-y-3">
        {/* Kontrol Filter Kategori */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-card border border-border p-2.5 rounded-xl shadow-sm">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 w-full sm:w-auto">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = activeCategory === cat.id;

              let count = facilities.length;
              if (cat.id === "School") count = schoolCount;
              if (cat.id === "Hospital") count = hospitalCount;
              if (cat.id === "Clinic") count = clinicCount;
              if (cat.id === "BusStop") count = busStopCount;
              if (cat.id === "Park") count = parkCount;

              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${isActive
                      ? `${cat.color} shadow-sm font-semibold`
                      : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50"
                    }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{cat.label}</span>
                  <span className={`px-1.5 py-0.2 text-[10px] rounded-full font-mono ${isActive ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
                    }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="text-xs text-muted-foreground font-medium hidden lg:block">
            Klik penanda untuk melihat detail fasilitas
          </div>
        </div>

        {/* Wadah Peta Utama */}
        <div className="h-[520px] w-full relative">
          {hasNoData ? (
            <div className="h-full w-full rounded-xl border border-border bg-card p-8 flex flex-col items-center justify-center text-center shadow-sm">
              <div className="h-14 w-14 rounded-full bg-muted flex items-center justify-center mb-4">
                <MapPin className="h-7 w-7 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Tidak Ada Data Spasial</h3>
              <p className="text-sm text-muted-foreground max-w-md mt-2">
                Data spasial dan fasilitas publik untuk <strong className="text-foreground">{selectedCity?.name}</strong> belum di-import ke dalam database spasial.
              </p>
              <div className="mt-4 p-3 bg-muted/40 border border-border rounded-lg text-xs font-mono text-muted-foreground max-w-lg">
                Jalankan: <code>docker exec sdgs-backend-1 python scripts/import_facilities.py --types School Hospital Clinic BusStop Park</code>
              </div>
            </div>
          ) : (
            <Map
              facilities={facilities}
              boundary={boundary}
              districts={districts}
              loading={isLoadingMap}
              activeFilter={activeCategory}
              onSelectFacility={(fac) => setSelectedFacility(fac)}
            />
          )}
        </div>
      </div>

      {/* Drawer Detail Fasilitas Yang Dipilih */}
      {selectedFacility && (
        <div className="bg-card border border-border p-4 rounded-xl shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center border border-primary/20">
              <Building2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h4 className="font-bold text-sm text-foreground">{selectedFacility.name}</h4>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                <span className="font-semibold uppercase text-primary">{selectedFacility.facility_type}</span>
                <span>•</span>
                <span>Lat: {selectedFacility.lat.toFixed(4)}, Lng: {selectedFacility.lng.toFixed(4)}</span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setSelectedFacility(null)}
            className="text-xs font-medium text-muted-foreground hover:text-foreground border border-border px-3 py-1.5 rounded-md hover:bg-muted"
          >
            Tutup Detail
          </button>
        </div>
      )}
    </div>
  );
}
