import { createContext, useContext, useState, useCallback } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const [username, setUsername] = useState(() => localStorage.getItem("admin_username") || "");

  const login = useCallback(async (user, pass) => {
    const form = new URLSearchParams();
    form.append("username", user);
    form.append("password", pass);
    const res = await client.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { access_token } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("admin_username", user);
    setToken(access_token);
    setUsername(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("admin_username");
    setToken(null);
    setUsername("");
  }, []);

  return (
    <AuthContext.Provider value={{ token, username, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
