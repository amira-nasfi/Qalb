import apiClient from "./client";
import type { Report } from "../types";

export const getReports = async (status?: string): Promise<Report[]> => {
  const url = status ? `/api/reports/?status=${status}` : "/api/reports/";
  const response = await apiClient.get<Report[]>(url);
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

/** Tele-interpretation: physician claims/takes ownership of a case */
export const claimReport = async (id: number | string): Promise<Report> => {
  const response = await apiClient.post<Report>(`/api/reports/${id}/claim/`);
  return response.data;
};

/** Tele-interpretation: physician requests ECG re-acquisition */
export const requestRetake = async (id: number | string, reason: string): Promise<Report> => {
  const response = await apiClient.post<Report>(`/api/reports/${id}/retake/`, { reason });
  return response.data;
};

/** Tele-interpretation: physician triggers SAMU vital emergency alert */
export const triggerEmergency = async (id: number | string, notes: string): Promise<Report> => {
  const response = await apiClient.post<Report>(`/api/reports/${id}/emergency/`, { notes });
  return response.data;
};
