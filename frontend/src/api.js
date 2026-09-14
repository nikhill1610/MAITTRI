import axios from "axios";

export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

const client = axios.create({ baseURL: API });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const clearAuthSession = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("user_id");
  localStorage.removeItem("full_name");
  localStorage.removeItem("email");
};

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear stale auth credentials
      clearAuthSession();
      
      // If user is not already on login/register/splash, redirect to login
      const path = window.location.pathname;
      if (path !== "/login" && path !== "/register" && path !== "/") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default client;
