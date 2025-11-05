import { useState } from "react";

import type { DatasetResponse } from "@/lib/api-client/api-client";

export const useDatasetsModalState = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState<DatasetResponse | null>(
    null
  );
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const openCreateModal = () => setIsCreateModalOpen(true);
  const closeCreateModal = () => setIsCreateModalOpen(false);

  const openEditModal = (dataset: DatasetResponse) => {
    setEditingDataset(dataset);
    setIsEditModalOpen(true);
  };

  const closeEditModal = () => {
    setIsEditModalOpen(false);
    setEditingDataset(null);
  };

  return {
    isCreateModalOpen,
    openCreateModal,
    closeCreateModal,
    editingDataset,
    isEditModalOpen,
    openEditModal,
    closeEditModal,
  };
};
