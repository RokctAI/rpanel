"use client";

import React from "react";
import { Server, HardDrive, Globe, Database, Mail } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function RPanelNav() {
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + "/");

  return (
    <aside className="w-64 border-r bg-muted/20 hidden md:block h-screen sticky top-0">
      <div className="p-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Server className="h-6 w-6 text-primary" />
          RPanel
        </h1>
      </div>
      <nav className="space-y-1 px-4">
        <Link
          href="/rpanel"
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${pathname === "/rpanel" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"}`}
        >
          <HardDrive className="h-4 w-4" /> Overview
        </Link>
        <Link
          href="/rpanel/websites"
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${isActive("/rpanel/websites") ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"}`}
        >
          <Globe className="h-4 w-4" /> Websites
        </Link>
        <Link
          href="/rpanel/databases"
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${isActive("/rpanel/databases") ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"}`}
        >
          <Database className="h-4 w-4" /> Databases
        </Link>
        <Link
          href="/rpanel/emails"
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${isActive("/rpanel/emails") ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"}`}
        >
          <Mail className="h-4 w-4" /> Emails
        </Link>
      </nav>
    </aside>
  );
}
