"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function createWebsite(data: { domain: string; site_type: string; client: string }) {
  const headers = await getHeadersWithCookies();
  try {
    const res = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        domain: data.domain,
        site_type: data.site_type,
        client: data.client,
        php_version: "8.2",
        status: "Active"
      })
    });

    const json = await res.json();
    if (json.exc) throw new Error(JSON.stringify(json.exc));
    return { success: true, data: json.data };
  } catch (e: any) {
    console.error(e);
    return { success: false, error: e.message };
  }
}
