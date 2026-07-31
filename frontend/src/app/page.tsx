import Link from "next/link";
import { 
  ArrowRight, 
  Map, 
  Activity, 
  Layers, 
  School, 
  Hospital, 
  Stethoscope, 
  Bus, 
  Trees
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      {/* Navigasi Header */}
      <header className="px-6 lg:px-12 h-16 flex items-center justify-between border-b border-border bg-background/95 backdrop-blur sticky top-0 z-50">
        <Link className="flex items-center gap-2.5" href="/">
          <span className="font-bold text-lg tracking-tight">Invisible City</span>
        </Link>
        <nav className="flex gap-4 items-center">
          <Link
            className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90"
            href="/dashboard"
          >
            Buka Dashboard
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Link>
        </nav>
      </header>

      <main className="flex-1">
        {/* Hero Section: Menjelaskan Invisible City dalam 5-10 Detik */}
        <section className="w-full py-16 md:py-24 lg:py-32 flex items-center justify-center bg-gradient-to-b from-background via-muted/30 to-background border-b border-border">
          <div className="container px-4 md:px-6 max-w-5xl">
            <div className="flex flex-col items-center space-y-6 text-center">
              
              {/* Pesan Utama Hero */}
              <div className="space-y-4 max-w-3xl">
                <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl md:text-6xl text-foreground">
                  Petakan Yang Tak Terlihat. <br className="hidden sm:inline" />
                  <span className="text-primary">Solusi Kesenjangan Aksesibilitas Perkotaan.</span>
                </h1>
                <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl/relaxed pt-2 leading-relaxed">
                  Invisible City mengukur keadilan layanan publik dalam konsep kota 15 menit. Kami menghitung skor <strong>Urban Fairness Score (UFS)</strong> di seluruh sekolah, rumah sakit, klinik, halte bus, dan taman untuk mendeteksi wilayah yang terisolasi.
                </p>
              </div>

              {/* Tombol Aksi Utama */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4 w-full sm:w-auto">
                <Link
                  href="/dashboard"
                  className="inline-flex h-12 items-center justify-center rounded-xl bg-primary px-8 text-base font-semibold text-primary-foreground shadow-md transition-all hover:bg-primary/90 hover:scale-[1.02]"
                >
                  Jelajahi Dashboard Interaktif
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex h-12 items-center justify-center rounded-xl border border-border bg-card px-6 text-base font-semibold text-foreground shadow-sm transition-colors hover:bg-muted"
                >
                  Masuk Akun
                </Link>
              </div>

            </div>
          </div>
        </section>

        {/* Penjelasan 5 Fasilitas Perkotaan */}
        <section className="w-full py-16 flex items-center justify-center border-b border-border bg-card">
          <div className="container px-4 md:px-6 max-w-5xl">
            <div className="text-center max-w-2xl mx-auto mb-12">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">5 Pilar Keadilan Perkotaan</h2>
              <p className="text-sm text-muted-foreground mt-2">
                Invisible City mengevaluasi keadilan akses publik di lima kategori fasilitas dasar perkotaan.
              </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-4 rounded-xl border border-border bg-background flex flex-col items-center text-center space-y-2 shadow-sm">
                <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-600">
                  <School className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-sm text-foreground">Sekolah</h3>
                <p className="text-xs text-muted-foreground">Akses pendidikan dasar & menengah</p>
              </div>

              <div className="p-4 rounded-xl border border-border bg-background flex flex-col items-center text-center space-y-2 shadow-sm">
                <div className="p-2.5 rounded-lg bg-red-500/10 text-red-600">
                  <Hospital className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-sm text-foreground">Rumah Sakit</h3>
                <p className="text-xs text-muted-foreground">Layanan kesehatan darurat & spesialis</p>
              </div>

              <div className="p-4 rounded-xl border border-border bg-background flex flex-col items-center text-center space-y-2 shadow-sm">
                <div className="p-2.5 rounded-lg bg-rose-500/10 text-rose-600">
                  <Stethoscope className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-sm text-foreground">Klinik</h3>
                <p className="text-xs text-muted-foreground">Puskesmas & pos kesehatan lokal</p>
              </div>

              <div className="p-4 rounded-xl border border-border bg-background flex flex-col items-center text-center space-y-2 shadow-sm">
                <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-600">
                  <Bus className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-sm text-foreground">Halte Bus</h3>
                <p className="text-xs text-muted-foreground">Koridor & titik transportasi publik</p>
              </div>

              <div className="p-4 rounded-xl border border-border bg-background flex flex-col items-center text-center space-y-2 shadow-sm col-span-2 md:col-span-1">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-600">
                  <Trees className="h-6 w-6" />
                </div>
                <h3 className="font-semibold text-sm text-foreground">Taman</h3>
                <p className="text-xs text-muted-foreground">Ruang terbuka hijau & rekreasi</p>
              </div>
            </div>
          </div>
        </section>

        {/* Fitur Utama */}
        <section className="w-full py-16 flex items-center justify-center">
          <div className="container px-4 md:px-6 max-w-5xl">
            <div className="grid md:grid-cols-3 gap-8">
              <div className="p-6 rounded-xl border border-border bg-card space-y-3 shadow-sm">
                <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Map className="h-5 w-5" />
                </div>
                <h3 className="font-bold text-lg text-foreground">Peta Spasial Terpadu</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Peta interaktif Leaflet yang menampilkan batas administratif kota, kecamatan, dan sebaran fasilitas perkotaan.
                </p>
              </div>

              <div className="p-6 rounded-xl border border-border bg-card space-y-3 shadow-sm">
                <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Activity className="h-5 w-5" />
                </div>
                <h3 className="font-bold text-lg text-foreground">Urban fairness score</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Algoritma penilaian keadilan spasial real-time yang membandingkan sebaran fasilitas nyata dengan target ideal kota 15 menit.
                </p>
              </div>

              <div className="p-6 rounded-xl border border-border bg-card space-y-3 shadow-sm">
                <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Layers className="h-5 w-5" />
                </div>
                <h3 className="font-bold text-lg text-foreground">Analisis Kesenjangan Akses</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Ringkasan wawasan kebijakan instan untuk mendeteksi kecamatan krisis fasilitas guna membantu perencanaan kota.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="py-6 w-full border-t border-border bg-card">
        <div className="container px-4 md:px-6 mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-2">
          <p>© 2026 Invisible City.</p>
          <div className="flex gap-4">
            <Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link>
            <Link href="/login" className="hover:text-foreground transition-colors">Masuk Akun</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
