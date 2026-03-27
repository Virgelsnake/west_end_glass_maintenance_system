import { createContext, useContext, useState, useCallback } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const [username, setUsername] = useState(() => localStorage.getItem("admin_username") || "");
  const [role, setRole] = useState(() => localStorage.getItem("admin_role") || "viewer");
  const [fullName, setFullName] = useState(() => localStorage.getItem("admin_full_name") || "");

  // Technician portal state (separate token)
  const [techToken, setTechToken] = useState(() => localStorage.getItem("tech_token"));
  const [techUser, setTechUser] = useState(() => {
    const stored = localStorage.getItem("tech_user");
    return stored ? JSON.parse(stored) : null;
  });

  const loginAdmin = useCallback(async (user, pass) => {
    const form = new URLSearchParams();
    form.append("username", user);
    form.append("password", pass);
    const res = await client.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { access_token, role: userRole, full_name } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("admin_username", user);
    localStorage.setItem("admin_role", userRole || "viewer");
    localStorage.setItem("admin_full_name", full_name || user);
    setToken(access_token);
    setUsername(user);
    setRole(userRole || "viewer");
    setFullName(full_name || user);
  }, []);

  // Keep legacy 'login' alias for existing code
  const login = loginAdmin;

  const loginTech = useCallback(async (phone, pin) => {
    const res = await client.post("/auth/technician/login", { phone_number: phone, pin });
    const { access_token, name, phone_number } = res.data;
    const techData = { phone_number, name };
    localStorage.setItem("tech_token", access_token);
    localStorage.setItem("tech_user", JSON.stringify(techData));
    setTechToken(access_token);
    setTechUser(techData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("admin_username");
    localStorage.removeItem("admin_role");
    localStorage.removeItem("admin_full_name");
    setToken(null);
    setUsername("");
    setRole("viewer");
    setFullName("");
  }, []);

  const logoutTech = useCallback(() => {
    localStorage.removeItem("tech_token");
    localStorage.removeItem("tech_user");
    setTechToken(null);
    setTechUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{
      token, username, role, fullName,
      login, loginAdmin, logout,
      isAuthenticated: !!token,
      techToken, techUser, loginTech, logoutTech,
      isTechAuthenticated: !!techToken,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
