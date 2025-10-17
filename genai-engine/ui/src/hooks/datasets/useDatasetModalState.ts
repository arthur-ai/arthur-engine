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

  isAddColumnDialogOpen: boolean;
  openAddColumnDialog: () => void;
  closeAddColumnDialog: () => void;

  isVersionDrawerOpen: boolean;
  openVersionDrawer: () => void;
  closeVersionDrawer: () => void;
}

export function useDatasetModalState(): UseDatasetModalStateReturn {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingRow, setEditingRow] =
    useState<DatasetVersionRowResponse | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAddColumnDialogOpen, setIsAddColumnDialogOpen] = useState(false);
  const [isVersionDrawerOpen, setIsVersionDrawerOpen] = useState(false);

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

  const openAddColumnDialog = () => setIsAddColumnDialogOpen(true);
  const closeAddColumnDialog = () => setIsAddColumnDialogOpen(false);

  const openVersionDrawer = () => setIsVersionDrawerOpen(true);
  const closeVersionDrawer = () => setIsVersionDrawerOpen(false);

  return {
    isEditModalOpen,
    editingRow,
    openEditModal,
    closeEditModal,
    isAddModalOpen,
    openAddModal,
    closeAddModal,
    isAddColumnDialogOpen,
    openAddColumnDialog,
    closeAddColumnDialog,
    isVersionDrawerOpen,
    openVersionDrawer,
    closeVersionDrawer,
  };
}
