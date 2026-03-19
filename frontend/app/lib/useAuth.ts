"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { authFetch, clearToken, getToken } from "./auth";

type UserProfile = {
  id: string;
  email: string;
  topics: string[];
};

type TokenPayload = {
  exp?: number;
  iat?: number;
};

function decodeToken(token: string): TokenPayload | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(normalized));
    return decoded as TokenPayload;
  } catch {
    return null;
  }
}

export function useAuth() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const timerRef = useRef<number | null>(null);
  const inactivityMs = 24 * 60 * 60 * 1000;

  useEffect(() => {
    void loadUser();
    startInactivityTimer();
    return () => clearInactivityTimer();
  }, []);

  async function loadUser() {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    const payload = decodeToken(token);
    if (payload?.exp && payload.exp * 1000 <= Date.now()) {
      await logout();
      return;
    }
    try {
      const res = await authFetch("/me");
      if (!res.ok) {
        clearToken();
        setUser(null);
        setLoading(false);
        return;
      }
      const data = (await res.json()) as UserProfile;
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  function clearInactivityTimer() {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    window.removeEventListener("mousemove", resetTimer);
    window.removeEventListener("keydown", resetTimer);
    window.removeEventListener("scroll", resetTimer);
    window.removeEventListener("click", resetTimer);
  }

  function resetTimer() {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      void logout();
    }, inactivityMs);
  }

  function startInactivityTimer() {
    resetTimer();
    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);
    window.addEventListener("scroll", resetTimer);
    window.addEventListener("click", resetTimer);
  }

  async function logout() {
    try {
      await authFetch("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
      setUser(null);
      router.push("/login");
    }
  }

  return { user, loading, logout };
}
