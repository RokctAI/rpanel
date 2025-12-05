"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function deleteWebsite(websiteName: string) {
  const headers = await getHeadersWithCookies();
  try {
    const res = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, {
      method: "DELETE",
      headers,
    });

    if (!res.ok) {
        const json = await res.json();
        throw new Error(JSON.stringify(json));
    }
    return { success: true };
  } catch (e: any) {
    console.error(e);
    return { success: false, error: e.message };
  }
}

export async function updateWebsite(websiteName: string, data: any) {
  const headers = await getHeadersWithCookies();
  try {
    const res = await fetch(`${BASE_URL}/v1/api/resource/Hosted Website/${websiteName}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data)
    });

    const json = await res.json();
    if (json.exc) throw new Error(JSON.stringify(json.exc));
    return { success: true, data: json.data };
  } catch (e: any) {
    console.error(e);
    return { success: false, error: e.message };
  }
}
