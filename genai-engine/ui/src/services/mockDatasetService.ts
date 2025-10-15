import { v4 as uuidv4 } from "uuid";

import {
  Dataset,
  DatasetFormData,
  DatasetFilters,
  DatasetVersion,
  PaginatedDatasets,
} from "@/types/dataset";

// In-memory storage for mock datasets
const mockDatasets: Map<string, Dataset[]> = new Map();

// Sample dataset names
const datasetNames = [
  "Customer Feedback Analysis",
  "Product Reviews Dataset",
  "Sales Performance Metrics",
  "User Behavior Tracking",
  "Marketing Campaign Results",
  "Support Ticket Analysis",
  "Website Analytics Data",
  "A/B Test Results",
  "Email Campaign Metrics",
  "Social Media Engagement",
];

// Sample owner names
const ownerNames = [
  "Alice Johnson",
  "Bob Smith",
  "Carol Williams",
  "David Brown",
  "Emma Davis",
  "Frank Miller",
];

/**
 * Generate mock datasets for a task
 */
function generateMockDatasets(taskId: string, count: number = 8): Dataset[] {
  const datasets: Dataset[] = [];
  const now = new Date();

  for (let i = 0; i < count; i++) {
    const createdDate = new Date(
      now.getTime() - Math.random() * 30 * 24 * 60 * 60 * 1000
    ); // Within last 30 days
    const lastModifiedDate = new Date(
      createdDate.getTime() +
        Math.random() * (now.getTime() - createdDate.getTime())
    );

    datasets.push({
      id: uuidv4(),
      name:
        datasetNames[i % datasetNames.length] +
        (i >= datasetNames.length
          ? ` ${Math.floor(i / datasetNames.length) + 1}`
          : ""),
      rowCount: Math.floor(Math.random() * 9900) + 100, // 100 to 10000
      columnCount: Math.floor(Math.random() * 23) + 3, // 3 to 25
      versionTag: `v1.${Math.floor(Math.random() * 5)}`,
      lastModified: lastModifiedDate.toISOString(),
      owner: ownerNames[Math.floor(Math.random() * ownerNames.length)],
      taskId,
      createdAt: createdDate.toISOString(),
      description: `Mock dataset for testing purposes - ${i + 1}`,
    });
  }

  return datasets;
}

/**
 * Initialize mock datasets for a task if they don't exist
 */
function ensureMockDatasets(taskId: string): void {
  if (!mockDatasets.has(taskId)) {
    mockDatasets.set(taskId, generateMockDatasets(taskId));
  }
}

/**
 * Simulate API delay
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Filter and sort datasets
 */
function filterAndSortDatasets(
  datasets: Dataset[],
  filters: DatasetFilters
): Dataset[] {
  let filtered = [...datasets];

  // Apply search filter
  if (filters.searchQuery && filters.searchQuery.trim()) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter((dataset) =>
      dataset.name.toLowerCase().includes(query)
    );
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let comparison = 0;

    switch (filters.sortBy) {
      case "name":
        comparison = a.name.localeCompare(b.name);
        break;
      case "lastModified":
        comparison =
          new Date(a.lastModified).getTime() -
          new Date(b.lastModified).getTime();
        break;
      case "createdAt":
        comparison =
          new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        break;
      case "rowCount":
        comparison = a.rowCount - b.rowCount;
        break;
    }

    return filters.sortOrder === "asc" ? comparison : -comparison;
  });

  return filtered;
}

/**
 * Fetch datasets with pagination, sorting, and search
 */
export async function fetchDatasets(
  taskId: string,
  filters: DatasetFilters
): Promise<PaginatedDatasets> {
  // Simulate API delay
  await delay(300 + Math.random() * 200);

  ensureMockDatasets(taskId);
  const allDatasets = mockDatasets.get(taskId) || [];
  const filtered = filterAndSortDatasets(allDatasets, filters);

  // Apply pagination
  const start = filters.page * filters.pageSize;
  const end = start + filters.pageSize;
  const paginatedDatasets = filtered.slice(start, end);

  return {
    datasets: paginatedDatasets,
    total: filtered.length,
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

/**
 * Create a new dataset
 */
export async function createDataset(
  taskId: string,
  formData: DatasetFormData
): Promise<Dataset> {
  // Simulate API delay
  await delay(400 + Math.random() * 200);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];

  const now = new Date().toISOString();
  const newDataset: Dataset = {
    id: uuidv4(),
    name: formData.name,
    description: formData.description,
    rowCount: 0,
    columnCount: 0,
    versionTag: "v1.0",
    lastModified: now,
    owner: "Current User", // In real implementation, this would come from auth context
    taskId,
    createdAt: now,
  };

  datasets.push(newDataset);
  mockDatasets.set(taskId, datasets);

  return newDataset;
}

/**
 * Get a dataset by ID
 */
export async function getDataset(
  taskId: string,
  datasetId: string
): Promise<Dataset | null> {
  // Simulate API delay
  await delay(200 + Math.random() * 100);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];
  return datasets.find((d) => d.id === datasetId) || null;
}

/**
 * Delete a dataset
 */
export async function deleteDataset(
  taskId: string,
  datasetId: string
): Promise<void> {
  // Simulate API delay
  await delay(400 + Math.random() * 300);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];
  const filteredDatasets = datasets.filter((d) => d.id !== datasetId);

  if (filteredDatasets.length === datasets.length) {
    throw new Error("Dataset not found");
  }

  mockDatasets.set(taskId, filteredDatasets);
}

/**
 * Update a row in a dataset
 */
export async function updateDatasetRow(
  taskId: string,
  datasetId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _rowId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _rowData: Record<string, unknown>
): Promise<void> {
  // Simulate API delay
  await delay(400 + Math.random() * 200);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];
  const dataset = datasets.find((d) => d.id === datasetId);

  if (!dataset) {
    throw new Error("Dataset not found");
  }

  // Update last modified timestamp
  dataset.lastModified = new Date().toISOString();

  // In a real implementation, this would update the actual row data
  // For now, we just update the metadata
}

/**
 * Delete a row from a dataset
 */
export async function deleteDatasetRow(
  taskId: string,
  datasetId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _rowId: string
): Promise<void> {
  // Simulate API delay
  await delay(300 + Math.random() * 200);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];
  const dataset = datasets.find((d) => d.id === datasetId);

  if (!dataset) {
    throw new Error("Dataset not found");
  }

  // Decrement row count
  if (dataset.rowCount > 0) {
    dataset.rowCount -= 1;
  }
  dataset.lastModified = new Date().toISOString();

  // In a real implementation, this would delete the actual row data
  // For now, we just update the metadata
}

/**
 * Generate mock versions for a dataset
 */
function generateMockVersions(
  datasetId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _datasetName: string
): DatasetVersion[] {
  const versions: DatasetVersion[] = [];
  const versionCount = Math.floor(Math.random() * 8) + 3; // 3 to 10 versions
  const now = new Date();

  for (let i = versionCount; i >= 1; i--) {
    const daysAgo = (versionCount - i) * Math.floor(Math.random() * 5 + 1);
    const createdAt = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000);

    versions.push({
      id: `${datasetId}-v${i}`,
      versionNumber: i,
      createdAt: createdAt.toISOString(),
      createdBy: ownerNames[Math.floor(Math.random() * ownerNames.length)],
      rowCount: Math.floor(Math.random() * 1000) + 100,
      columnCount: Math.floor(Math.random() * 10) + 5,
      changes:
        i === 1
          ? "Initial version"
          : [
              "Updated schema",
              "Added new rows",
              "Fixed data quality issues",
              "Merged from staging",
              "Applied transformations",
              "Cleaned outliers",
            ][Math.floor(Math.random() * 6)],
      isCurrent: i === versionCount,
    });
  }

  return versions;
}

/**
 * Fetch versions for a dataset
 */
export async function fetchDatasetVersions(
  taskId: string,
  datasetId: string
): Promise<DatasetVersion[]> {
  // Simulate API delay
  await delay(300 + Math.random() * 200);

  ensureMockDatasets(taskId);
  const datasets = mockDatasets.get(taskId) || [];
  const dataset = datasets.find((d) => d.id === datasetId);

  if (!dataset) {
    throw new Error("Dataset not found");
  }

  // Generate versions for this dataset
  return generateMockVersions(datasetId, dataset.name);
}

/**
 * Clear all mock data (useful for testing)
 */
export function clearMockData(): void {
  mockDatasets.clear();
}
