import apiClient from "./client";
import type { ProcessingResult } from "../types";

export interface ECGUploadResponse {
  job_id: number;
  status_url: string;
  status: string;
}

export interface ECGStatusResponse {
  id: number;
  status: "PENDING" | "PROCESSING" | "DONE" | "ERROR";
  error_message: string;
  uploaded_at: string;
  result_url: string | null;
}

export interface ECGSignalResponse {
  samples: number[];
  r_peaks: number[];
  fs_display: number;
  unit: string;
}

export const uploadECG = async (
  file: File,
  pseudo_id: string,
  fmt: string,
  onUploadProgress?: (progressEvent: any) => void
): Promise<ECGUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("pseudo_id", pseudo_id);
  formData.append("fmt", fmt);

  const response = await apiClient.post<ECGUploadResponse>("/api/ecg/upload/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress,
  });
  return response.data;
};

export const getECGStatus = async (jobId: number | string): Promise<ECGStatusResponse> => {
  const response = await apiClient.get<ECGStatusResponse>(`/api/ecg/${jobId}/status/`);
  return response.data;
};

export const getECGResult = async (jobId: number | string): Promise<ProcessingResult> => {
  const response = await apiClient.get<ProcessingResult>(`/api/ecg/${jobId}/result/`);
  return response.data;
};

export const getECGSignal = async (
  jobId: number | string,
  lead: string = "II",
  downsample: number = 500
): Promise<ECGSignalResponse> => {
  const response = await apiClient.get<ECGSignalResponse>(
    `/api/ecg/${jobId}/signal/?lead=${lead}&downsample=${downsample}`
  );
  return response.data;
};
