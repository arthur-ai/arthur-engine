import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import React, { useState, useEffect } from "react";

import { useUpdateVersionTags } from "@/hooks/rag-search-settings/useUpdateVersionTags";
import useSnackbar from "@/hooks/useSnackbar";
import { COMMON_TAGS } from "@/lib/constants";

interface VersionTagsDialogProps {
  open: boolean;
  onClose: () => void;
  configId: string;
  versionNumber: number;
  currentTags: string[];
  allPossibleTags: string[];
}

export const VersionTagsDialog: React.FC<VersionTagsDialogProps> = ({ open, onClose, configId, versionNumber, currentTags, allPossibleTags }) => {
  const [tags, setTags] = useState<string[]>([]);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const updateTags = useUpdateVersionTags();

  useEffect(() => {
    if (open) {
      setTags(currentTags);
    }
  }, [open, currentTags]);

  const handleSave = async () => {
    try {
      await updateTags.mutateAsync({
        configId,
        versionNumber,
        tags,
      });
      showSnackbar("Tags updated successfully", "success");
      onClose();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to update tags";
      showSnackbar(errorMessage, "error");
    }
  };

  const handleClose = () => {
    setTags(currentTags);
    onClose();
  };

  const suggestedTags = Array.from(new Set([...COMMON_TAGS, ...allPossibleTags]));

  return (
    <>
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Tags for Version {versionNumber}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 pt-2">
            <Autocomplete
              multiple
              freeSolo
              options={suggestedTags}
              value={tags}
              onChange={(_e, newValue) => setTags(newValue)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => {
                  const { key, ...tagProps } = getTagProps({ index });
                  return <Chip key={key} label={option} variant="outlined" {...tagProps} />;
                })
              }
              renderInput={(params) => <TextField {...params} label="Tags" placeholder="Add tags..." />}
            />

            <div>
              <div className="text-sm text-gray-600 mb-2">Suggested tags:</div>
              <div className="flex flex-wrap gap-2">
                {COMMON_TAGS.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    size="small"
                    variant="outlined"
                    onClick={() => {
                      if (!tags.includes(tag)) {
                        setTags([...tags, tag]);
                      }
                    }}
                    sx={{ cursor: "pointer" }}
                  />
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={updateTags.isPending}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
