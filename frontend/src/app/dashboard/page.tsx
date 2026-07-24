export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground">
          Welcome to the Invisible City dashboard. View your city's public facility metrics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Placeholder cards */}
        <div className="rounded-xl border bg-card text-card-foreground shadow">
          <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">Average UFS</h3>
          </div>
          <div className="p-6 pt-0">
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">
              Awaiting calculation...
            </p>
          </div>
        </div>
        
        <div className="rounded-xl border bg-card text-card-foreground shadow">
          <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">Total Facilities</h3>
          </div>
          <div className="p-6 pt-0">
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">
              Awaiting data ingestion...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
