import { useCallback, useState } from "react";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export interface UseDatasetModalStateReturn {
  isEditModalOpen: boolean;
  editingRow: DatasetVersionRowResponse | null;
  openEditModal: (row: DatasetVersionRowResponse) => void;
  closeEditModal: () => void;

  isAddModalOpen: boolean;
  openAddModal: () => void;
  closeAddModal: () => void;

  isConfigureColumnsOpen: boolean;
  openConfigureColumns: () => void;
  closeConfigureColumns: () => void;

  isVersionDrawerOpen: boolean;
  openVersionDrawer: () => void;
  closeVersionDrawer: () => void;

  isImportModalOpen: boolean;
  openImportModal: () => void;
  closeImportModal: () => void;
}

export function useDatasetModalState(): UseDatasetModalStateReturn {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingRow, setEditingRow] =
    useState<DatasetVersionRowResponse | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isConfigureColumnsOpen, setIsConfigureColumnsOpen] = useState(false);
  const [isVersionDrawerOpen, setIsVersionDrawerOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const openEditModal = useCallback((row: DatasetVersionRowResponse) => {
    setEditingRow(row);
    setIsEditModalOpen(true);
  }, []);

  const closeEditModal = () => {
    setIsEditModalOpen(false);
    setEditingRow(null);
  };

  const openAddModal = () => setIsAddModalOpen(true);
  const closeAddModal = () => setIsAddModalOpen(false);

  const openConfigureColumns = () => setIsConfigureColumnsOpen(true);
  const closeConfigureColumns = () => setIsConfigureColumnsOpen(false);

  const openVersionDrawer = () => setIsVersionDrawerOpen(true);
  const closeVersionDrawer = () => setIsVersionDrawerOpen(false);

  const openImportModal = () => setIsImportModalOpen(true);
  const closeImportModal = () => setIsImportModalOpen(false);

  return {
    isEditModalOpen,
    editingRow,
    openEditModal,
    closeEditModal,
    isAddModalOpen,
    openAddModal,
    closeAddModal,
    isConfigureColumnsOpen,
    openConfigureColumns,
    closeConfigureColumns,
    isVersionDrawerOpen,
    openVersionDrawer,
    closeVersionDrawer,
    isImportModalOpen,
    openImportModal,
    closeImportModal,
  };
}
