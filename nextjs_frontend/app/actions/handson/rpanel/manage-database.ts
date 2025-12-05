"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function getDatabases(clientName: string) {
    const headers = await getHeadersWithCookies();
    try {
        const res = await fetch(`${BASE_URL}/v1/api/method/rpanel.hosting.doctype.hosting_client.hosting_client.get_client_databases`, {
            method: "GET",
            headers,
            cache: "no-store"
        });

        if (!res.ok) throw new Error("Failed to fetch databases");
        const json = await res.json();
        return { success: true, data: json.message.databases };
    } catch (e: any) {
        return { success: false, error: e.message };
    }
}

export async function updateDatabasePassword(websiteName: string, newPassword: string) {
    const headers = await getHeadersWithCookies();
    try {
        const res = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, {
            method: "PUT",
            headers,
            body: JSON.stringify({ db_password: newPassword })
        });

        const json = await res.json();
        if (json.exc) throw new Error(JSON.stringify(json.exc));
        return { success: true };
    } catch (e: any) {
        return { success: false, error: e.message };
    }
}
