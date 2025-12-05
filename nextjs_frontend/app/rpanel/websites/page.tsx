"use client";

import React, { useEffect, useState } from "react";
import { Globe, Plus, Trash2, Edit, MoreVertical, RefreshCw } from "lucide-react";
import { getClientWebsites } from "@/app/actions/handson/rpanel/get-client-websites";
import { deleteWebsite } from "@/app/actions/handson/rpanel/manage-website";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RPanelNav } from "@/components/custom/nav/rpanel-nav";

export default function WebsitesPage() {
  const [websites, setWebsites] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchWebsites = async () => {
    setIsLoading(true);
    const res = await getClientWebsites();
    if (res.message?.success) {
      setWebsites(res.message.websites);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchWebsites();
  }, []);

  const handleDelete = async (name: string) => {
    if (confirm("Are you sure you want to delete this website? This action cannot be undone.")) {
      const res = await deleteWebsite(name);
      if (res.success) {
        fetchWebsites();
      } else {
        alert("Failed to delete website: " + res.error);
      }
    }
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <RPanelNav />
      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Websites</h1>
          <Button onClick={() => alert("Use Dashboard to Create")}>
            <Plus className="mr-2 h-4 w-4" /> New Website
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground font-medium">
                <tr>
                  <th className="px-6 py-4">Domain</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Type</th>
                  <th className="px-6 py-4">SSL</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {websites.map((site) => (
                  <tr key={site.name} className="hover:bg-muted/50">
                    <td className="px-6 py-4 font-medium">{site.domain}</td>
                    <td className="px-6 py-4">{site.status}</td>
                    <td className="px-6 py-4">{site.site_type}</td>
                    <td className="px-6 py-4">{site.ssl_status}</td>
                    <td className="px-6 py-4 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuItem onClick={() => alert("Edit logic here")}>
                            <Edit className="mr-2 h-4 w-4" /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDelete(site.name)} className="text-red-600">
                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
