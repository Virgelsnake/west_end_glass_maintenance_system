import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE,
});

// Attach JWT token to every request (admin or tech)
client.interceptors.request.use((config) => {
  const isTechRoute = config.url?.startsWith("/tech") || config.url?.startsWith("/auth/technician");
  const token = isTechRoute
    ? localStorage.getItem("tech_token")
    : localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      if (url.startsWith("/tech")) {
        localStorage.removeItem("tech_token");
        localStorage.removeItem("tech_user");
        window.location.href = "/tech/login";
      } else {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export default client;
