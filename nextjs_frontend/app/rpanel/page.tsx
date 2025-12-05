"use client";

import React, { useEffect, useState } from "react";
import { Globe, HardDrive, Database, RefreshCw, AlertCircle } from "lucide-react";
import { useSession } from "next-auth/react";
import { getClientUsage } from "../actions/handson/rpanel/get-client-usage";
import { RPanelNav } from "../../components/custom/nav/rpanel-nav";

// --- Components ---

const StatCard = ({ title, used, limit, icon: Icon, unit = "" }: any) => {
  const percentage = Math.min((used / limit) * 100, 100);
  const color = percentage > 90 ? "bg-red-500" : "bg-blue-600";

  return (
    <div className="bg-card text-card-foreground rounded-lg border shadow-sm p-6">
      <div className="flex flex-row items-center justify-between pb-2">
        <h3 className="tracking-tight text-sm font-medium text-muted-foreground">{title}</h3>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="content">
        <div className="text-2xl font-bold">{used} <span className="text-sm font-normal text-muted-foreground">/ {limit} {unit}</span></div>
        <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
          <div className={`h-full ${color}`} style={{ width: `${percentage}%` }}></div>
        </div>
      </div>
    </div>
  );
};

export default function RPanelDashboard() {
  const { data: session } = useSession();
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const statsData = await getClientUsage();

      if (statsData.message?.success) {
        setStats(statsData.message.usage);
      } else {
        if (session) console.warn("Failed to load dashboard data.");
      }

    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (session) {
        fetchDashboardData();
    }
  }, [session]);

  if (!session) {
      return <div className="p-8 text-center">Please log in to access RPanel.</div>;
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <RPanelNav />

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
            <div className="flex gap-2">
                <button
                    onClick={fetchDashboardData}
                    className="p-2 rounded-md border hover:bg-muted"
                    title="Refresh"
                >
                    <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </div>
        </div>

        {error && (
            <div className="bg-red-50 text-red-900 p-4 rounded-md mb-6 border border-red-200 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" />
                {error}
            </div>
        )}

        {/* Overview Tab */}
        {stats && (
            <div className="space-y-8">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    <StatCard
                        title="Websites"
                        used={stats.websites.used}
                        limit={stats.websites.limit}
                        icon={Globe}
                    />
                    <StatCard
                        title="Storage"
                        used={stats.storage_gb.used}
                        limit={stats.storage_gb.limit}
                        unit="GB"
                        icon={HardDrive}
                    />
                    <StatCard
                        title="Databases"
                        used={stats.databases.used}
                        limit={stats.databases.limit}
                        icon={Database}
                    />
                </div>

                <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
                    <div className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
                        <div className="text-sm text-muted-foreground">No recent activity logs found.</div>
                    </div>
                </div>
            </div>
        )}
      </main>
    </div>
  );
}
