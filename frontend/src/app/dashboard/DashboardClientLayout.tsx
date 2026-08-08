"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import {
  Map,
  LogOut,
  LayoutDashboard,
  BarChart3,
  Menu,
  X,
  Home
} from "lucide-react";
import { GeographicProvider } from "@/context/GeographicContext";
import CitySelector from "@/components/CitySelector";

export default function DashboardClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Set demo token secara non-blocking — layout langsung dirender
  useEffect(() => {
    if (!Cookies.get("access_token")) {
      Cookies.set("access_token", "demo_guest_token", { expires: 1 });
    }
  }, []);

  const handleLogout = () => {
    Cookies.remove("access_token");
    router.push("/");
  };

  const navItems = [
    { href: "/dashboard", label: "Ringkasan", icon: LayoutDashboard },
    { href: "/dashboard/map", label: "Peta Interaktif", icon: Map },
    { href: "/dashboard/analysis", label: "Analisis Keadilan", icon: BarChart3 },
  ];

  return (
    <GeographicProvider>
      <div className="flex min-h-screen bg-background text-foreground">
        {/* Sidebar Desktop */}
        <aside className="w-64 flex-shrink-0 border-r border-border bg-card hidden md:flex flex-col">
          <div className="h-16 flex items-center px-6 border-b border-border bg-background">
            <Link className="flex items-center gap-2.5" href="/dashboard">
              <span className="font-bold text-base tracking-tight">Invisible City</span>
            </Link>
          </div>

          <nav className="p-4 space-y-1.5 flex-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-semibold transition-all ${isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-border bg-muted/20 space-y-2">
            <Link
              href="/"
              className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground p-2 rounded-md hover:bg-muted transition-colors"
            >
              <Home className="h-4 w-4" />
              Halaman Utama
            </Link>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 w-full text-xs font-medium text-red-500 hover:text-red-600 p-2 rounded-md hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Keluar Akun
            </button>
          </div>
        </aside>

        {/* Ruang Kerja Konten Utama */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-border bg-background sticky top-0 z-40">
            <div className="flex items-center gap-3">
              {/* Tombol Menu Mobile */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted"
                aria-label="Buka Menu Navigasi"
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hidden sm:inline">Kota:</span>
                <CitySelector />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/"
                className="text-xs font-medium text-muted-foreground hover:text-foreground border border-border px-2.5 py-1 rounded-lg hover:bg-muted transition-colors"
              >
                Keluar
              </Link>
            </div>
          </header>

          {/* Menu Drawer Mobile */}
          {mobileMenuOpen && (
            <div className="md:hidden border-b border-border bg-card p-4 space-y-2 animate-in slide-in-from-top-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold ${isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
                      }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
              <div className="pt-2 border-t border-border flex items-center justify-between">
                <Link href="/" className="text-xs text-muted-foreground">Halaman Utama</Link>
                <button onClick={handleLogout} className="text-xs text-red-500 font-semibold">Keluar Akun</button>
              </div>
            </div>
          )}

          {/* Body Halaman */}
          <main className="flex-1 p-4 md:p-6 bg-muted/20 overflow-x-hidden">
            {children}
          </main>
        </div>
      </div>
    </GeographicProvider>
  );
}
