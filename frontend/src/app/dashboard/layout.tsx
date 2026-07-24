"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import { Map, LogOut, LayoutDashboard, Settings } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const token = Cookies.get("access_token");
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  if (!mounted) return null;

  const handleLogout = () => {
    Cookies.remove("access_token");
    router.push("/");
  };

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 flex-shrink-0 border-r bg-muted/40 hidden md:block">
        <div className="h-16 flex items-center px-6 border-b bg-background">
          <Link className="flex items-center gap-2" href="/dashboard">
            <Map className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg">Invisible City</span>
          </Link>
        </div>
        <nav className="p-4 space-y-2">
          <Link
            href="/dashboard"
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              pathname === "/dashboard" 
                ? "bg-primary text-primary-foreground" 
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <LayoutDashboard className="h-4 w-4" />
            Overview
          </Link>
          <Link
            href="/dashboard/map"
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              pathname === "/dashboard/map" 
                ? "bg-primary text-primary-foreground" 
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Map className="h-4 w-4" />
            Interactive Map
          </Link>
          {/* Add more links later */}
        </nav>
      </aside>
      
      <div className="flex-1 flex flex-col">
        <header className="h-16 flex items-center justify-between px-6 border-b bg-background">
          <div className="md:hidden">
            <span className="font-bold">Invisible City</span>
          </div>
          <div className="ml-auto flex items-center gap-4">
            <button className="text-muted-foreground hover:text-foreground p-2 rounded-full transition-colors">
              <Settings className="h-5 w-5" />
            </button>
            <button 
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground p-2 rounded-full transition-colors"
              title="Logout"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </header>
        <main className="flex-1 p-6 bg-muted/20">
          {children}
        </main>
      </div>
    </div>
  );
}
