"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function getEmailAccounts(clientName: string) {
    const headers = await getHeadersWithCookies();
    try {
        const res = await fetch(`${BASE_URL}/v1/api/method/rpanel.hosting.doctype.hosting_client.hosting_client.get_client_emails`, {
            method: "GET",
            headers,
            cache: "no-store"
        });

        if (!res.ok) throw new Error("Failed to fetch emails");
        const json = await res.json();
        return { success: true, data: json.message.emails };
    } catch (e: any) {
        return { success: false, error: e.message };
    }
}

export async function createEmailAccount(websiteName: string, account: { email_user: string, password: string, quota_mb: number }) {
    const headers = await getHeadersWithCookies();
    try {
        // 1. Get current doc
        const getRes = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, { headers });
        const doc = (await getRes.json()).data;

        // 2. Append row
        const newAccounts = [...(doc.email_accounts || []), {
            email_user: account.email_user,
            password: account.password,
            quota_mb: account.quota_mb,
            doctype: "Hosted Email Account"
        }];

        // 3. Update doc
        const updateRes = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, {
            method: "PUT",
            headers,
            body: JSON.stringify({ email_accounts: newAccounts })
        });

        const json = await updateRes.json();
        if (json.exc) throw new Error(JSON.stringify(json.exc));
        return { success: true };

    } catch (e: any) {
        return { success: false, error: e.message };
    }
}

export async function deleteEmailAccount(websiteName: string, emailUser: string) {
    const headers = await getHeadersWithCookies();
    try {
        const getRes = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, { headers });
        const doc = (await getRes.json()).data;

        const newAccounts = (doc.email_accounts || []).filter((acc: any) => acc.email_user !== emailUser);

        const updateRes = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, {
            method: "PUT",
            headers,
            body: JSON.stringify({ email_accounts: newAccounts })
        });

        const json = await updateRes.json();
        if (json.exc) throw new Error(JSON.stringify(json.exc));
        return { success: true };

    } catch (e: any) {
        return { success: false, error: e.message };
    }
}
