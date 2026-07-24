"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";

interface AnalyticsData {
  overall_score: number;
  total_facilities: number;
  breakdown: Record<string, number>;
  status: string;
}

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const token = Cookies.get("access_token");
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/analytics/ufs`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (response.ok) {
          const json = await response.json();
          setData(json);
        }
      } catch (error) {
        console.error("Failed to fetch analytics:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground">
          Welcome to the Invisible City dashboard. View your city's public facility metrics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-card text-card-foreground shadow">
          <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">Average UFS</h3>
          </div>
          <div className="p-6 pt-0">
            {loading ? (
              <div className="text-2xl font-bold animate-pulse text-muted">...</div>
            ) : (
              <>
                <div className="text-2xl font-bold">{data?.overall_score ?? "--"}</div>
                <p className="text-xs text-muted-foreground">
                  Status: {data?.status ?? "Unknown"}
                </p>
              </>
            )}
          </div>
        </div>
        
        <div className="rounded-xl border bg-card text-card-foreground shadow">
          <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">Total Facilities</h3>
          </div>
          <div className="p-6 pt-0">
            {loading ? (
              <div className="text-2xl font-bold animate-pulse text-muted">...</div>
            ) : (
              <>
                <div className="text-2xl font-bold">{data?.total_facilities ?? "--"}</div>
                <p className="text-xs text-muted-foreground">
                  Across all types
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
