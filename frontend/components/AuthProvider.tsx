"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AuthUser, Session } from "@/lib/api";
import { getMe } from "@/lib/api";

const STORAGE_KEY = "eews_session";
const SESSION_COOKIE = "eews_token";

function syncSessionCookie(session: Session | null) {
  if (typeof document === "undefined") return;
  if (session) {
    document.cookie = `${SESSION_COOKIE}=${encodeURIComponent(session.token)}; path=/; SameSite=Lax; max-age=86400`;
  } else {
    document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0`;
  }
}

type AuthContextValue = {
  session: Session | null;
  setSession: (s: Session | null) => void;
  ready: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    async function hydrate() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw) as Session;
        if (parsed.expiresAt && Date.now() > parsed.expiresAt) {
          localStorage.removeItem(STORAGE_KEY);
          syncSessionCookie(null);
          return;
        }
        await getMe(parsed.token);
        setSessionState(parsed);
        syncSessionCookie(parsed);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        syncSessionCookie(null);
      } finally {
        setReady(true);
      }
    }
    void hydrate();
  }, []);

  function setSession(s: Session | null) {
    setSessionState(s);
    if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    else localStorage.removeItem(STORAGE_KEY);
    syncSessionCookie(s);
  }

  return (
    <AuthContext.Provider value={{ session, setSession, ready }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useUser(): AuthUser | null {
  return useAuth().session?.user ?? null;
}
