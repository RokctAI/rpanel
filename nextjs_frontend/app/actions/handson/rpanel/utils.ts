"use server";

import { auth } from "@/auth";
import { cookies } from "next/headers";

export const BASE_URL = process.env.ROKCT_BASE_URL || "";

export async function getHeadersWithCookies() {
    const cookieStore = cookies();

    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };

    // Try to get Frappe session cookie if it exists (same domain)
    const sid = cookieStore.get("sid");
    if (sid) {
        headers["Cookie"] = `sid=${sid.value}`;
    }

    // Also check session for API Keys
    const session = await auth();
    if (session && (session.user as any).apiKey && (session.user as any).apiSecret) {
         headers["Authorization"] = `token ${(session.user as any).apiKey}:${(session.user as any).apiSecret}`;
    }

    return headers;
}
