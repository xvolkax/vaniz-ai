import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "@/lib/api";
import type { TokenResponse, Tenant, User, UserRole } from "@/lib/types";

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  ready: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (min: UserRole) => boolean;
}

const ROLE_RANK: Record<UserRole, number> = {
  viewer: 0,
  agent: 1,
  admin: 2,
  owner: 3,
};

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [ready, setReady] = useState(false);

  const loadSession = useCallback(async () => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    try {
      const [me, myTenant] = await Promise.all([
        api.get<User>("/auth/me"),
        api.get<Tenant>("/tenants/me"),
      ]);
      setUser(me);
      setTenant(myTenant);
    } catch {
      setToken(null);
      setUser(null);
      setTenant(null);
    } finally {
      setReady(true);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setTenant(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setTenant(null);
    });
    void loadSession();
    return () => setUnauthorizedHandler(null);
  }, [loadSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.post<TokenResponse>("/auth/login", { email, password });
      setToken(res.access_token);
      const [me, myTenant] = await Promise.all([
        api.get<User>("/auth/me"),
        api.get<Tenant>("/tenants/me"),
      ]);
      setUser(me);
      setTenant(myTenant);
    },
    []
  );

  const hasRole = useCallback(
    (min: UserRole) => (user ? ROLE_RANK[user.role] >= ROLE_RANK[min] : false),
    [user]
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      tenant,
      ready,
      isAuthenticated: !!user,
      login,
      logout,
      hasRole,
    }),
    [user, tenant, ready, login, logout, hasRole]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
