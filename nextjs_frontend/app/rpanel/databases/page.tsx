"use client";

import React, { useEffect, useState } from "react";
import { Database, Lock, RefreshCw } from "lucide-react";
import { getDatabases, updateDatabasePassword } from "@/app/actions/handson/rpanel/manage-database";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RPanelNav } from "@/components/custom/nav/rpanel-nav";
import { useSession } from "next-auth/react";

export default function DatabasesPage() {
  const { data: session } = useSession();
  const [databases, setDatabases] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDBs = async () => {
    setIsLoading(true);
    const res = await getDatabases("");
    if (res.success) {
      setDatabases(res.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchDBs();
  }, []);

  const handlePasswordChange = async (name: string) => {
    const newPass = prompt("Enter new database password:");
    if (newPass) {
        const res = await updateDatabasePassword(name, newPass);
        if (res.success) alert("Password updated");
        else alert("Failed: " + res.error);
    }
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <RPanelNav />
      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Databases</h1>
          <Button onClick={fetchDBs} variant="outline">
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {databases.map((db) => (
            <Card key={db.name}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {db.db_name}
                </CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-xs text-muted-foreground mb-4">User: {db.db_user}</div>
                <div className="text-xs text-muted-foreground mb-4">Host: localhost</div>
                <Button variant="secondary" size="sm" className="w-full" onClick={() => handlePasswordChange(db.name)}>
                    <Lock className="mr-2 h-3 w-3" /> Reset Password
                </Button>
              </CardContent>
            </Card>
          ))}
          {databases.length === 0 && !isLoading && (
              <div className="col-span-full text-center text-muted-foreground p-8">
                  No databases found. Databases are created automatically with CMS sites.
              </div>
          )}
        </div>
      </main>
    </div>
  );
}
