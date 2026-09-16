import apiClient from "./client";

export const getFHIRExport = async (reportId: number | string): Promise<any> => {
  const response = await apiClient.get(`/api/fhir/reports/${reportId}/`);
  return response.data;
};

export const downloadFHIRExport = async (reportId: number | string, filename?: string) => {
  const data = await getFHIRExport(reportId);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/fhir+json" });
  const url = window.URL.createObjectURL(blob);
  
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `fhir_report_${reportId}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
