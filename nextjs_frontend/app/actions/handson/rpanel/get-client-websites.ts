"use server";

import { getHeadersWithCookies, BASE_URL } from "./utils";

export async function getClientWebsites() {
  const headers = await getHeadersWithCookies();
  try {
    const res = await fetch(`${BASE_URL}/v1/api/method/rpanel.hosting.doctype.hosting_client.hosting_client.get_client_websites`, {
      method: "GET",
      headers,
      cache: "no-store"
    });

    if (!res.ok) throw new Error("Failed to fetch websites");
    return await res.json();
  } catch (e) {
    console.error(e);
    return { message: { success: false } };
  }
}
