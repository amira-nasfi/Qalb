import apiClient from "./client";

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  action: string;
  actor: string;
  target_type: string;
  target_id: string;
  ip_address_hash: string;
  extra: any;
  hash_signature: string;
}

export const getAuditLogs = async (): Promise<AuditLogEntry[]> => {
  const response = await apiClient.get("/api/admin/audit/");
  if (response.data && "results" in response.data) {
    return (response.data as any).results;
  }
  return response.data as AuditLogEntry[];
};

export interface UserItem {
  id: number;
  username: string;
  email: string;
  full_name: string;
  first_name: string;
  last_name: string;
  role: "FIELD_AGENT" | "PHYSICIAN" | "ADMIN";
  organization: string;
  is_suspended: boolean;
  last_login: string;
  date_joined: string;
}

export const getUsers = async (): Promise<UserItem[]> => {
  const response = await apiClient.get<UserItem[]>("/api/admin/users/");
  if (response.data && "results" in (response.data as any)) {
    return (response.data as any).results;
  }
  return response.data;
};

export const inviteUser = async (data: any): Promise<UserItem> => {
  const response = await apiClient.post<UserItem>("/api/admin/users/invite/", data);
  return response.data;
};

export const toggleUserSuspend = async (userId: number): Promise<{ id: number; is_suspended: boolean }> => {
  const response = await apiClient.post(`/api/admin/users/${userId}/suspend/`);
  return response.data;
};

export const changeUserRole = async (userId: number, role: string): Promise<UserItem> => {
  const response = await apiClient.patch(`/api/admin/users/${userId}/role/`, { role });
  return response.data;
};
