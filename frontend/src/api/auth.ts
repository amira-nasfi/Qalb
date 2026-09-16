import apiClient from "./client";

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: "FIELD_AGENT" | "PHYSICIAN" | "ADMIN";
  organization: string;
  phone: string;
  is_suspended: boolean;
  last_login: string;
  date_joined: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: UserProfile;
}

export const login = async (username: string, password: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>("/api/auth/login/", {
    username,
    password,
  });
  return response.data;
};

export const logout = async (refreshToken: string): Promise<void> => {
  try {
    await apiClient.post("/api/auth/logout/", { refresh: refreshToken });
  } catch (error) {
    console.error("Logout error", error);
  }
};

export const getMe = async (): Promise<UserProfile> => {
  const response = await apiClient.get<UserProfile>("/api/auth/me/");
  return response.data;
};
