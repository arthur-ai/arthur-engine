import { useState } from "react";

import { Dataset } from "@/types/dataset";

export const useDatasetsModalState = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const openCreateModal = () => setIsCreateModalOpen(true);
  const closeCreateModal = () => setIsCreateModalOpen(false);

  const openEditModal = (dataset: Dataset) => {
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
