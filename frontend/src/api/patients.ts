import apiClient from "./client";
import type { Patient } from "../types";

export const getPatients = async (search?: string): Promise<Patient[]> => {
  const url = search ? `/api/patients/?search=${encodeURIComponent(search)}` : "/api/patients/";
  const response = await apiClient.get<any>(url);
  if (response.data && "results" in response.data) {
    return response.data.results;
  }
  return Array.isArray(response.data) ? response.data : [];
};

export const createPatient = async (data: Partial<Patient>): Promise<Patient> => {
  const response = await apiClient.post<Patient>("/api/patients/", data);
  return response.data;
};

export const getPatient = async (pseudo_id: string): Promise<Patient> => {
  const response = await apiClient.get<Patient>(`/api/patients/${pseudo_id}/`);
  return response.data;
};
