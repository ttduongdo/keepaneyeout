export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("auth_token");
}

export function setToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("auth_token", token);
}

export function clearToken() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem("auth_token");
}

import { getApiBase } from "./apiBase";

const apiBase = getApiBase();

function withApiBase(input: RequestInfo): RequestInfo {
  if (typeof input === "string" && input.startsWith("/")) {
    return `${apiBase}${input}`;
  }
  return input;
}

export async function authFetch(input: RequestInfo, init: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(withApiBase(input), { ...init, headers });
}
