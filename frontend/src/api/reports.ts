import apiClient from "./client";
import type { Report } from "../types";

export const getReports = async (status?: string): Promise<Report[]> => {
  const url = status ? `/api/reports/?status=${status}` : "/api/reports/";
  const response = await apiClient.get<Report[]>(url);
  // DRF returns paginated results by default, but we assume we either handle pagination
  // or return the flat array. Let's assume the API returns the results array.
  // Actually DRF default is paginated: { count, next, previous, results }
  // To keep types simple, we assume the interceptor or we unwrap it here:
  if (response.data && "results" in response.data) {
    return (response.data as any).results;
  }
  return response.data as unknown as Report[];
};

export const getReport = async (id: number | string): Promise<Report> => {
  const response = await apiClient.get<Report>(`/api/reports/${id}/`);
  return response.data;
};

export const updateReportNotes = async (id: number | string, notes: string): Promise<Report> => {
  const response = await apiClient.patch<Report>(`/api/reports/${id}/`, {
    physician_notes: notes,
  });
  return response.data;
};

export const signReport = async (id: number | string): Promise<Report> => {
  const response = await apiClient.post<Report>(`/api/reports/${id}/sign/`);
  return response.data;
};
