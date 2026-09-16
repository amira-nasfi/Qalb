import axios, { AxiosError } from "axios";

// Default base URL fallback for local development
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL,
  withCredentials: true, // For session/CSRF cookies if used
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: add JWT and CSRF
apiClient.interceptors.request.use((config) => {
  // Add JWT
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }

  // Add CSRF
  const csrfToken = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];

  if (csrfToken) {
    config.headers["X-CSRFToken"] = csrfToken;
  }
  
  return config;
});

// Response interceptor: handle 401 and silent refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    // Prevent infinite loop if the refresh itself fails
    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== "/api/auth/refresh/") {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        try {
          const response = await axios.post(`${baseURL}/api/auth/refresh/`, {
            refresh: refreshToken,
          });

          // Save new tokens
          localStorage.setItem("access_token", response.data.access);
          if (response.data.refresh) {
             localStorage.setItem("refresh_token", response.data.refresh);
          }

          // Retry the original request
          originalRequest.headers["Authorization"] = `Bearer ${response.data.access}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          console.error("Refresh failed", refreshError);
          // Clear tokens and let the UI handle the redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.dispatchEvent(new Event("auth_refresh_failed"));
        }
      } else {
        window.dispatchEvent(new Event("auth_refresh_failed"));
      }
    }

    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
