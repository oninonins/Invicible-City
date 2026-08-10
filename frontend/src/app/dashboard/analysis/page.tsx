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
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";
import { useGeographic } from "@/context/GeographicContext";
import { API_BASE } from "@/lib/api";

interface AnalyticsData {
  overall_score: number;
  total_facilities: number;
  breakdown: Record<string, number>;
  status: string;
}

interface Deficit {
  indicator: string;
  score: number;
  action: string;
}

interface RecommendationItem {
  rank: number;
  district_id: number;
  name: string | null;
  overall_score: number;
  category: string;
  deficit_count: number;
  weakest_score: number | null;
  deficits: Deficit[];
  recommended_actions: string[];
}

interface Recommendation {
  city_id: number;
  city_name: string | null;
  methodology: string;
  generated_at: string | null;
  summary: string;
  status?: string | null;
  recommendation_available?: boolean;
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

const CATEGORY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  Critical: { bg: "bg-red-500/10", text: "text-red-600 dark:text-red-400", border: "border-red-500/20" },
  Poor: { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", border: "border-amber-500/20" },
  Fair: { bg: "bg-yellow-500/10", text: "text-yellow-600 dark:text-yellow-400", border: "border-yellow-500/20" },
  Good: { bg: "bg-emerald-500/10", text: "text-emerald-600 dark:text-emerald-400", border: "border-emerald-500/20" },
  Excellent: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", border: "border-blue-500/20" },
};

export default function AnalysisPage() {
  const { selectedCity } = useGeographic();
  const [llmMode, setLlmMode] = useState(false);
  const [expandedDistricts, setExpandedDistricts] = useState<Record<number, boolean>>({});
  const [showAllDistricts, setShowAllDistricts] = useState(false);

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
    refetch: refetchRecs,
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

  const toggleDistrictDetails = (id: number) => {
    setExpandedDistricts(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

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

  const isSparseData = !isLoading && (total === 0 || score === 0);
  const priorityList = recommendations?.priority || [];
  const visiblePriority = showAllDistricts ? priorityList : priorityList.slice(0, 5);

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

      {/* Warning jika data coverage terbatas / No Data */}
      {isSparseData && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3 text-amber-600 dark:text-amber-400">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <h4 className="text-xs font-bold uppercase tracking-wider">Data coverage terbatas</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Skor dan rekomendasi pada wilayah dengan data fasilitas terbatas harus diperlakukan sebagai indikasi awal dan memerlukan verifikasi lapangan.
            </p>
          </div>
        </div>
      )}

      {/* Banner Ringkasan Skor UFS */}
      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div className="grid md:grid-cols-3 gap-6 items-center">
          
          <div className="flex items-center gap-5">
            <div className="relative flex items-center justify-center h-24 w-24 rounded-full border-4 border-primary/20 bg-primary/5">
              <span className="text-3xl font-extrabold text-foreground font-mono">
                {isLoading ? "..." : score.toFixed(1)}
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

      {/* Rekomendasi Prioritas & AI Insight */}
      <div className="space-y-4 pt-2">
        {/* Header Rekomendasi */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              Rekomendasi Prioritas
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Deterministic ranking berdasarkan UFS, jumlah defisit, dan indikator terlemah.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/80">
              RULE ENGINE: PENENTU PRIORITAS
            </span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
              AI: PENJELASAN
            </span>
          </div>
        </div>

        {/* Panel AI Insight */}
        {recommendations?.narrative ? (
          <div className="rounded-xl border border-primary/25 bg-primary/5 p-4 sm:p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-foreground">Analisis AI</h4>
                  <p className="text-[11px] text-muted-foreground">Narasi berbasis data UFS dan prioritas yang dihitung sistem</p>
                </div>
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                AI Explanation
              </span>
            </div>

            <div className="text-xs sm:text-sm text-foreground/90 leading-relaxed whitespace-pre-line border-t border-primary/15 pt-3">
              {recommendations.narrative}
            </div>

            <div className="pt-2 border-t border-primary/10 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <span>Berdasarkan data fasilitas UFS v0 · Generated by Nemotron 3 Ultra</span>
              <button
                onClick={() => refetchRecs()}
                disabled={fetchingRecs}
                className="inline-flex items-center gap-1 text-primary hover:underline transition-colors cursor-pointer text-[11px] font-medium"
              >
                <RotateCcw className={`h-3 w-3 ${fetchingRecs ? 'animate-spin' : ''}`} />
                Muat ulang narasi
              </button>
            </div>
          </div>
        ) : recError && llmMode ? (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-foreground">Analisis AI tidak tersedia saat ini</h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Rekomendasi berbasis rule engine tetap tersedia.
                </p>
              </div>
            </div>
            <button
              onClick={() => refetchRecs()}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-foreground transition-colors cursor-pointer"
            >
              Coba lagi
            </button>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-sm space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <h4 className="text-sm font-bold text-foreground">Analisis AI</h4>
                </div>
                <p className="text-xs text-muted-foreground max-w-xl leading-relaxed">
                  Dapatkan penjelasan berbasis data mengenai wilayah prioritas dan indikator yang paling membutuhkan perhatian.
                </p>
              </div>
              <button
                onClick={() => setLlmMode(true)}
                disabled={fetchingRecs}
                className={`inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shadow-sm ${
                  fetchingRecs
                    ? "bg-muted text-muted-foreground cursor-wait"
                    : "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-[1.01]"
                }`}
              >
                {fetchingRecs ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Menganalisis...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Jelaskan dengan AI</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* State Loading & Error Rekomendasi Utama */}
        {loadingRecs ? (
          <div className="bg-card border border-border rounded-xl p-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Menghitung prioritas rule engine...
          </div>
        ) : recError && !recommendations ? (
          <div className="bg-card border border-destructive/30 rounded-xl p-6 flex items-center gap-3 text-sm text-muted-foreground">
            <AlertCircle className="h-5 w-5 text-destructive" />
            Gagal mengambil rekomendasi. Coba lagi nanti.
          </div>
        ) : !recommendations || priorityList.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-6 text-sm text-muted-foreground text-center">
            Belum ada rekomendasi. Pilih kota untuk menganalisis prioritas kecamatan.
          </div>
        ) : (
          <div className="space-y-3">
            {/* Analytical Summary Line */}
            {recommendations.summary && (
              <div className="p-3 bg-muted/40 border border-border/70 rounded-xl flex items-center gap-2.5 text-xs text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0" />
                <span className="leading-relaxed">{recommendations.summary}</span>
              </div>
            )}

            {/* List of Priority District Cards */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground px-1">
                <span>Daftar Wilayah Prioritas</span>
                <span>Menampilkan {visiblePriority.length} dari {priorityList.length} kecamatan</span>
              </div>

              {visiblePriority.map((item) => {
                const isExpanded = !!expandedDistricts[item.district_id];
                const catStyle = CATEGORY_STYLES[item.category] || { bg: "bg-muted", text: "text-foreground", border: "border-border" };

                return (
                  <div
                    key={item.district_id}
                    className="bg-card border border-border rounded-xl p-3.5 sm:p-4 shadow-sm space-y-3 transition-colors hover:border-border/90"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <div className="flex items-center gap-3">
                        <span className="h-7 w-7 rounded-lg bg-muted border border-border/60 flex items-center justify-center text-xs font-bold font-mono text-foreground">
                          #{item.rank}
                        </span>
                        <div>
                          <h4 className="text-sm font-bold text-foreground">{item.name || `Kecamatan ${item.district_id}`}</h4>
                          <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5">
                            <span className="font-mono font-semibold text-foreground">UFS {item.overall_score.toFixed(1)}</span>
                            <span>•</span>
                            <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold border ${catStyle.bg} ${catStyle.text} ${catStyle.border}`}>
                              {item.category}
                            </span>
                            <span>•</span>
                            <span>{item.deficit_count} defisit</span>
                          </div>
                        </div>
                      </div>

                      {item.recommended_actions.length > 0 && (
                        <button
                          onClick={() => toggleDistrictDetails(item.district_id)}
                          className="self-end sm:self-center inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer px-2 py-1 rounded hover:bg-muted"
                        >
                          <span>{isExpanded ? "Tutup detail" : "Lihat detail"}</span>
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                      )}
                    </div>

                    {item.deficits.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {item.deficits.map((d) => (
                          <span
                            key={d.indicator}
                            className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-destructive/10 text-destructive border border-destructive/20"
                            title={`Skor: ${d.score}`}
                          >
                            {DEFICIT_LABELS[d.indicator] || d.indicator}
                          </span>
                        ))}
                      </div>
                    )}

                    {isExpanded && item.recommended_actions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/60 bg-muted/20 rounded-lg p-3 space-y-2 animate-in fade-in slide-in-from-top-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block">
                          Rekomendasi Tindakan (Rule Engine)
                        </span>
                        <ul className="space-y-1.5">
                          {item.recommended_actions.map((action, idx) => (
                            <li key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                              <span className="text-primary font-bold mt-0.5">•</span>
                              <span className="leading-relaxed">{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}

              {priorityList.length > 5 && (
                <div className="text-center pt-2">
                  <button
                    onClick={() => setShowAllDistricts(prev => !prev)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-card hover:bg-muted text-xs font-semibold text-foreground transition-all cursor-pointer shadow-sm"
                  >
                    <span>{showAllDistricts ? "Tampilkan lebih sedikit" : `Tampilkan ${priorityList.length - 5} kecamatan lainnya`}</span>
                    {showAllDistricts ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
