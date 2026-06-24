"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type AuthContextType = {
  token: string | null;
  selectedRepoId: number | null;
  setSelectedRepoId: (id: number | null) => void;
  login: (token: string) => void;
  logout: () => void;
  isLoading: boolean;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [selectedRepoId, setSelectedRepoIdState] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // load session on refresh
  useEffect(() => {
    const saved = localStorage.getItem("token");
    if (saved) {
      setToken(saved);
    }
    const savedRepo = localStorage.getItem("selectedRepoId");
    if (savedRepo) {
      setSelectedRepoIdState(Number(savedRepo));
    }
    setIsLoading(false);
  }, []);

  const setSelectedRepoId = (id: number | null) => {
    if (id) {
      localStorage.setItem("selectedRepoId", String(id));
    } else {
      localStorage.removeItem("selectedRepoId");
    }
    setSelectedRepoIdState(id);
  };

  const login = (token: string) => {
    localStorage.setItem("token", token);
    setToken(token);
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("selectedRepoId");
    setToken(null);
    setSelectedRepoIdState(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ token, selectedRepoId, setSelectedRepoId, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}