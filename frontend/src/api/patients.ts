import apiClient from "./client";
import type { Patient } from "../types";

export const createPatient = async (data: Omit<Patient, "pseudo_id" | "created_at">): Promise<Patient> => {
  const response = await apiClient.post<Patient>("/api/patients/", data);
  return response.data;
};

export const getPatient = async (pseudo_id: string): Promise<Patient> => {
  const response = await apiClient.get<Patient>(`/api/patients/${pseudo_id}/`);
  return response.data;
};
