"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function getClientUsage() {
  const headers = await getHeadersWithCookies();
  try {
    const res = await fetch(`${BASE_URL}/v1/api/method/rpanel.hosting.doctype.hosting_client.hosting_client.get_client_usage`, {
      method: "GET",
      headers,
      cache: "no-store"
    });

    if (!res.ok) throw new Error("Failed to fetch usage");
    return await res.json();
  } catch (e) {
    console.error(e);
    return { message: { success: false } };
  }
}
