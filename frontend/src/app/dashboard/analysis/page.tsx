"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Cookies from "js-cookie";
import {
  BarChart3,
  Sparkles,
  Lightbulb,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";
import { API_BASE } from "@/lib/api";

interface AnalyticsData {
  overall_score: number;
  total_facilities: number;
  breakdown: Record<string, number>;
  status: string;
}

interface RecommendationItem {
  rank: number;
  district_id: number;
  name: string | null;
  overall_score: number;
  category: string;
  deficit_count: number;
  weakest_score: number | null;
  deficits: { indicator: string; score: number; action: string }[];
  recommended_actions: string[];
}

interface Recommendation {
  city_id: number;
  city_name: string | null;
  methodology: string;
  generated_at: string | null;
  summary: string;
  priority: RecommendationItem[];
  narrative: string | null;
}

const DEFICIT_LABELS: Record<string, string> = {
  education: "Pendidikan",
  healthcare: "Kesehatan",
  transportation: "Transportasi",
  public_space: "Ruang Terbuka",
  accessibility: "Aksesibilitas",
};

export default function AnalysisPage() {
  const { selectedCity } = useGeographic();
  const [llmMode, setLlmMode] = useState(false);

  // Ambil data analitik UFS
  const { data: analytics, isLoading } = useQuery<AnalyticsData>({
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

  // Ambil rekomendasi prioritas (rule engine, opsional narasi LLM)
  const {
    data: recommendations,
    isLoading: loadingRecs,
    isFetching: fetchingRecs,
    error: recError,
  } = useQuery<Recommendation | null>({
    queryKey: ['recommendations', selectedCity?.id, llmMode],
    queryFn: async () => {
      if (!selectedCity?.id) return null;
      const token = Cookies.get("access_token");
      const res = await fetch(
        `${API_BASE}/analytics/recommendations?city_id=${selectedCity.id}&llm=${llmMode}`,
        { headers: token ? { "Authorization": `Bearer ${token}` } : {} }
      );
      if (!res.ok) throw new Error("Gagal mengambil rekomendasi");
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
  const busStopCount = breakdown['BusStop'] || 0;
  const parkCount = breakdown['Park'] || 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-primary" />
            Urban fairness score & Analisis Aksesibilitas
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
                Benchmark: median kepadatan nasional per kecamatan
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
              <strong className="text-foreground">Median nasional / km²</strong>
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
            <div>
              <span className="text-xs font-bold text-blue-600 uppercase">Sekolah</span>
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{schoolCount}</div>
            <div className="text-[11px] text-muted-foreground">Pendidikan dasar & menengah</div>
          </div>

          {/* Rumah Sakit */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div>
              <span className="text-xs font-bold text-red-600 uppercase">Rumah Sakit</span>
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{hospitalCount}</div>
            <div className="text-[11px] text-muted-foreground">Pusat kesehatan darurat</div>
          </div>

          {/* Klinik */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div>
              <span className="text-xs font-bold text-rose-600 uppercase">Klinik</span>
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{clinicCount}</div>
            <div className="text-[11px] text-muted-foreground">Puskesmas & kesehatan lokal</div>
          </div>

          {/* Halte Bus */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2">
            <div>
              <span className="text-xs font-bold text-amber-600 uppercase">Halte Bus</span>
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{busStopCount}</div>
            <div className="text-[11px] text-muted-foreground">Titik akses transportasi</div>
          </div>

          {/* Taman */}
          <div className="bg-card border border-border p-4 rounded-xl shadow-sm space-y-2 col-span-2 sm:col-span-1">
            <div>
              <span className="text-xs font-bold text-emerald-600 uppercase">Taman</span>
            </div>
            <div className="text-2xl font-bold text-foreground font-mono">{parkCount}</div>
            <div className="text-[11px] text-muted-foreground">Ruang hijau & rekreasi</div>
          </div>

        </div>
      </div>

      {/* Rekomendasi Prioritas */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              Rekomendasi Prioritas
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Deterministik dari rule engine (UFS terendah, jumlah defisit, indikator terlemah).
            </p>
          </div>
          <button
            onClick={() => setLlmMode((prev) => !prev)}
            disabled={fetchingRecs}
            className={`text-xs font-medium px-3 py-1.5 rounded-md border transition-all cursor-pointer ${llmMode
                ? "bg-primary/10 text-primary border-primary/30"
                : "bg-muted/50 hover:bg-muted text-muted-foreground border-border/60"
              } ${fetchingRecs ? "opacity-60 cursor-wait" : ""}`}
          >
            {fetchingRecs ? (
              <span className="inline-flex items-center gap-1.5">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Memproses...
              </span>
            ) : llmMode ? (
              "Narasi AI Aktif"
            ) : (
              "Jelaskan dengan AI"
            )}
          </button>
        </div>

        {loadingRecs ? (
          <div className="bg-card border border-border rounded-xl p-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Menghitung rekomendasi...
          </div>
        ) : recError ? (
          <div className="bg-card border border-destructive/30 rounded-xl p-6 flex items-center gap-3 text-sm text-muted-foreground">
            <AlertCircle className="h-5 w-5 text-destructive" />
            Gagal mengambil rekomendasi. Coba lagi nanti.
          </div>
        ) : !recommendations || recommendations.priority.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-6 text-sm text-muted-foreground text-center">
            Belum ada rekomendasi. Pilih kota untuk menganalisis prioritas kecamatan.
          </div>
        ) : (
          <div className="space-y-3">
            {recommendations.narrative && (
              <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 text-sm text-foreground/90 leading-relaxed">
                <div className="flex items-center gap-1.5 text-xs font-bold text-primary mb-1.5">
                  <Sparkles className="h-3.5 w-3.5" />
                  Narasi AI
                </div>
                {recommendations.narrative}
              </div>
            )}

            <p className="text-xs text-muted-foreground leading-relaxed">
              {recommendations.summary}
            </p>

            <div className="space-y-2.5">
              {recommendations.priority.slice(0, 10).map((item) => (
                <div key={item.district_id} className="bg-card border border-border rounded-xl p-4 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold font-mono text-foreground">
                        {item.rank}
                      </span>
                      <div>
                        <span className="text-sm font-bold text-foreground">{item.name || `Kecamatan ${item.district_id}`}</span>
                        <span className="block text-[11px] text-muted-foreground">
                          UFS {item.overall_score} · {item.category} · {item.deficit_count} defisit
                        </span>
                      </div>
                    </div>
                  </div>

                  {item.deficits.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {item.deficits.map((d) => (
                        <span
                          key={d.indicator}
                          className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-destructive/10 text-destructive border border-destructive/20"
                          title={`Skor ${d.score}`}
                        >
                          {DEFICIT_LABELS[d.indicator] || d.indicator}
                        </span>
                      ))}
                    </div>
                  )}

                  {item.recommended_actions.length > 0 && (
                    <ul className="mt-3 space-y-1">
                      {item.recommended_actions.map((action, idx) => (
                        <li key={idx} className="text-xs text-muted-foreground flex items-start gap-1.5">
                          <span className="text-primary mt-0.5">•</span>
                          {action}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
