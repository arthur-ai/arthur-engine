export function downloadFile(content: string | Blob, filename: string, mimeType: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function downloadJson(data: unknown, baseFilename: string): void {
  const timestamp = new Date().toISOString().split("T")[0];
  const content = JSON.stringify(data, null, 2);
  downloadFile(content, `${baseFilename}-${timestamp}.json`, "application/json");
}

export function downloadCsv(csvContent: string, baseFilename: string): void {
  const timestamp = new Date().toISOString().split("T")[0];
  downloadFile(csvContent, `${baseFilename}-${timestamp}.csv`, "text/csv;charset=utf-8;");
}
