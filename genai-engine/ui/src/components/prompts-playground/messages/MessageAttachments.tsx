import AudioFileIcon from "@mui/icons-material/AudioFile";
import DeleteIcon from "@mui/icons-material/Delete";
import ImageIcon from "@mui/icons-material/Image";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Snackbar from "@mui/material/Snackbar";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback } from "react";

import { fileToImageItem } from "../utils/messageUtils";

import type { AttachmentDraft } from "./MessageComponent";

import useSnackbar from "@/hooks/useSnackbar";

// Cap the size of an inlined attachment; large base64 blobs bloat state and requests.
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024; // 10 MB
const MAX_ATTACHMENT_MB = MAX_ATTACHMENT_BYTES / (1024 * 1024);

interface MessageAttachmentsProps {
  attachments: AttachmentDraft[];
  onChange: (next: AttachmentDraft[]) => void;
}

export const MessageAttachments: React.FC<MessageAttachmentsProps> = ({ attachments, onChange }) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  // Audio uploads are intentionally omitted for now: the backend forwards
  // input_audio blocks to non-audio-capable models, which fail. The audio
  // conversion/render plumbing (messageUtils, the input_audio chip case below)
  // is kept dormant so it can be re-enabled once the backend supports it.
  const handleFiles = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      // Reset so selecting the same file again re-fires the change event.
      event.target.value = "";
      if (files.length === 0) return;

      const drafts: AttachmentDraft[] = [];
      for (const file of files) {
        if (file.type && !file.type.startsWith("image/")) {
          showSnackbar(`"${file.name}" is not a valid image file`, "error");
          continue;
        }
        if (file.size > MAX_ATTACHMENT_BYTES) {
          showSnackbar(`"${file.name}" exceeds the ${MAX_ATTACHMENT_MB} MB limit`, "error");
          continue;
        }
        try {
          const item = await fileToImageItem(file);
          drafts.push({ id: crypto.randomUUID(), item });
        } catch (error) {
          const message = error instanceof Error ? error.message : `Failed to read "${file.name}"`;
          showSnackbar(message, "error");
        }
      }

      if (drafts.length > 0) {
        onChange([...attachments, ...drafts]);
      }
    },
    [attachments, onChange, showSnackbar]
  );

  const handleRemove = useCallback(
    (id: string) => {
      onChange(attachments.filter((draft) => draft.id !== id));
    },
    [attachments, onChange]
  );

  const renderAttachment = (draft: AttachmentDraft) => {
    const { item } = draft;
    switch (item.type) {
      case "image_url":
        return (
          <Box
            key={draft.id}
            sx={{
              position: "relative",
              width: 72,
              height: 72,
              borderRadius: 1,
              overflow: "hidden",
              border: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <Box
              component="img"
              src={item.image_url?.url ?? ""}
              alt="attachment preview"
              sx={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
            <Tooltip title="Remove image" placement="top" arrow>
              <IconButton
                aria-label="remove image"
                size="small"
                onClick={() => handleRemove(draft.id)}
                sx={{
                  position: "absolute",
                  top: 2,
                  right: 2,
                  backgroundColor: "background.paper",
                  "&:hover": { backgroundColor: "action.hover" },
                }}
              >
                <DeleteIcon fontSize="small" color="error" />
              </IconButton>
            </Tooltip>
          </Box>
        );
      case "input_audio":
        return (
          <Chip
            key={draft.id}
            icon={<AudioFileIcon />}
            label={`Audio (${item.input_audio?.format ?? "unknown"})`}
            onDelete={() => handleRemove(draft.id)}
            deleteIcon={<DeleteIcon />}
            variant="outlined"
          />
        );
      case "text":
        // Attachments never contain text parts; nothing to render.
        return null;
      default: {
        const _exhaustive: never = item.type;
        return _exhaustive;
      }
    }
  };

  return (
    <Box sx={{ mt: 1 }}>
      <Stack direction="row" spacing={1}>
        <Button component="label" variant="outlined" size="small" startIcon={<ImageIcon />}>
          Add image
          <input type="file" hidden accept="image/*" onChange={handleFiles} />
        </Button>
      </Stack>
      {attachments.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", gap: 1 }}>
          {attachments.map((draft) => renderAttachment(draft))}
        </Stack>
      )}
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </Box>
  );
};
