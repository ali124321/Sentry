export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchApi(endpoint: string) {
  return fetch(`${API_URL}${endpoint}`);
}
