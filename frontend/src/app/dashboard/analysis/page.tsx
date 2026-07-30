"use client";

import { useQuery } from "@tanstack/react-query";
import Cookies from "js-cookie";
import { 
  BarChart3, 
  CheckCircle2, 
  AlertTriangle, 
  School, 
  Hospital, 
  Stethoscope, 
  Bus, 
  Trees, 
  HelpCircle,
  MapPin,
  Sparkles
} from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";

interface AnalyticsData {
  overall_score: number;
  total_facilities: number;
  breakdown: Record<string, number>;
  status: string;
}

export default function AnalysisPage() {
  const { selectedCity } = useGeographic();

  // Ambil data analitik UFS
  const { data: analytics, isLoading } = useQuery<AnalyticsData>({
    queryKey: ['analytics', selectedCity?.id],
    queryFn: async () => {
      if (!selectedCity?.id) return null;
      const token = Cookies.get("access_token");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/analytics/ufs?city_id=${selectedCity.id}`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error("Gagal mengambil data analitik");
      return res.json();
    },
    enabled: !!selectedCity?.id,
  });

  const score = analytics?.overall_score ?? 0;
  const rawStatus = analytics?.status ?? "";
  const statusStr = rawStatus === "Good" ? "Baik" : rawStatus === "Fair" ? "Cukup" : rawStatus === "Poor" ? "Kurang" : "Tidak Ada Data";
  const total = analytics?.total_facilities ?? 0;
  const breakdown = analytics?.breakdown ?? {};

  const schoolCount = breakdown['School'] || 0;
  const hospitalCount = breakdown['Hospital'] || 0;
  const clinicCount = breakdown['Clinic'] || 0;
  const busStopCount = breakdown['BusStop'] || breakdown['Bus Stop'] || 0;
  const parkCount = breakdown['Park'] || 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-primary" />
            Skor Keadilan Perkotaan (UFS) & Analisis Aksesibilitas
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Evaluasi kuantitatif keadilan dan aksesibilitas fasilitas publik untuk <strong className="text-foreground">{selectedCity?.name}</strong>.
          </p>
        </div>
      </div>

      {/* Banner Ringkasan Skor UFS */}
      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div className="grid md:grid-cols-3 gap-6 items-center">
          
          <div className="flex items-center gap-5">
            <div className="relative flex items-center justify-center h-24 w-24 rounded-full border-4 border-primary/20 bg-primary/5">
              <span className="text-3xl font-extrabold text-foreground font-mono">
                {isLoading ? "..." : score}
              </span>
              <span className="absolute text-[9px] font-mono text-muted-foreground bottom-2">/ 100</span>
            </div>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rating Keadilan Perkotaan</span>
              <h2 className="text-xl font-bold text-foreground mt-0.5">Keadilan {statusStr}</h2>
              <span className="inline-block text-xs text-muted-foreground mt-1">
                Target Acuan: 20 fasilitas publik / kecamatan
              </span>
            </div>
          </div>

          <div className="space-y-2 border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-6">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Total Titik Fasilitas Terpeta:</span>
              <strong className="text-foreground">{total} titik</strong>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Target Baselines Cakupan:</span>
              <strong className="text-foreground">20.0 / kecamatan</strong>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden mt-2">
              <div 
                className="bg-primary h-full rounded-full transition-all duration-500" 
                style={{ width: `${Math.min(score, 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-muted/40 border border-border/60 p-4 rounded-lg space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              Ringkasan Evaluasi
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {score >= 70 
                ? "Distribusi aksesibilitas sangat baik di 5 kategori layanan dasar perkotaan." 
                : score >= 40 
                ? "Aksesibilitas cukup merata namun membutuhkan penambahan di sektor transportasi atau kesehatan." 
                : "Terdapat defisit fasilitas yang membutuhkan investasi infrastruktur terarah."}
            </p>
          </div>

        </div>
      </div>

      {/* 5 Metrik Kategori Fasilitas */}
      <div className="space-y-3">
        <h3 className="text-base font-bold text-foreground">Rincian Per Kategori vs Target Ideal</h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          
          {/* Sekolah */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-600 uppercase">Sekolah</span>
              <School className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{schoolCount}</div>
            <div className="text-[11px] text-muted-foreground">Pendidikan dasar & menengah</div>
          </div>

          {/* Rumah Sakit */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-red-600 uppercase">Rumah Sakit</span>
              <Hospital className="h-4 w-4 text-red-600" />
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{hospitalCount}</div>
            <div className="text-[11px] text-muted-foreground">Pusat kesehatan darurat</div>
          </div>

          {/* Klinik */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-rose-600 uppercase">Klinik</span>
              <Stethoscope className="h-4 w-4 text-rose-600" />
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{clinicCount}</div>
            <div className="text-[11px] text-muted-foreground">Puskesmas & kesehatan lokal</div>
          </div>

          {/* Halte Bus */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-600 uppercase">Halte Bus</span>
              <Bus className="h-4 w-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{busStopCount}</div>
            <div className="text-[11px] text-muted-foreground">Titik akses transportasi</div>
          </div>

          {/* Taman */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2 col-span-2 sm:col-span-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-600 uppercase">Taman</span>
              <Trees className="h-4 w-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{parkCount}</div>
            <div className="text-[11px] text-muted-foreground">Ruang hijau & rekreasi</div>
          </div>

        </div>
      </div>

      {/* Panduan Pertanyaan Juri Kompetisi */}
      <div className="space-y-3">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-primary" />
          Panduan Pertanyaan Juri (Kejelasan 10 Detik)
        </h3>

        <div className="grid md:grid-cols-2 gap-4">
          
          <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <CheckCircle2 className="h-4 w-4" />
              1. Apa itu Invisible City?
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Platform intelijen spasial AI & PostGIS yang mengukur keadilan layanan publik 15 menit dan memetakan wilayah terisolasi.
            </p>
          </div>

          <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <MapPin className="h-4 w-4" />
              2. Kota mana yang sedang dianalisis?
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Saat ini menganalisis <strong className="text-foreground">{selectedCity?.name}</strong> berdasarkan batas administratif kecamatan dan sebaran klaster fasilitas OSM.
            </p>
          </div>

          <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <BarChart3 className="h-4 w-4" />
              3. Berapa Skor Keadilan Perkotaan (UFS)?
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Skor Keadilan Perkotaan adalah <strong className="text-foreground">{score} / 100 (Keadilan {statusStr})</strong>, dihitung secara dinamis dari rasio ketersediaan fasilitas publik.
            </p>
          </div>

          <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-amber-600 font-bold text-sm">
              <AlertTriangle className="h-4 w-4" />
              4. Di mana kesenjangan aksesibilitas & aksi apa yang diperlukan?
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {hospitalCount + clinicCount < 5 
                ? "Defisit layanan kesehatan primer terdeteksi. Rekomendasi: tempatkan pos puskesmas pembantu di kecamatan terluar." 
                : "Defisit fasilitas halte bus terdeteksi. Rekomendasi: tambah rute pengumpan transportasi publik."}
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}
