import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import { SxProps, Theme } from "@mui/material/styles";
import TextField from "@mui/material/TextField";
import Typography, { TypographyProps } from "@mui/material/Typography";
import { useEffect, useState } from "react";

interface EditableTitleProps {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  isPending?: boolean;
  fallbackText?: string;
  showEditButton?: boolean;
  typographyVariant?: TypographyProps["variant"];
  typographySx?: SxProps<Theme>;
  textFieldSx?: SxProps<Theme>;
}

export const EditableTitle = ({
  value,
  onSave,
  isPending = false,
  fallbackText = "",
  showEditButton = true,
  typographyVariant = "h6",
  typographySx,
  textFieldSx,
}: EditableTitleProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [inputValue, setInputValue] = useState(value);

  useEffect(() => {
    setInputValue(value);
  }, [value]);

  const handleStart = () => {
    setInputValue(value);
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setInputValue(value);
  };

  const handleSave = async () => {
    if (isPending) return;
    const trimmed = inputValue.trim();
    if (!trimmed || trimmed === value) {
      handleCancel();
      return;
    }
    setIsEditing(false);
    await onSave(trimmed);
  };

  if (isEditing) {
    return (
      <TextField
        variant="filled"
        size="small"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSave();
          else if (e.key === "Escape") handleCancel();
        }}
        onBlur={handleSave}
        autoFocus
        sx={{
          "& .MuiInputBase-root": { fontSize: "1.25rem", fontWeight: 600 },
          ...textFieldSx,
        }}
      />
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
      <Typography variant={typographyVariant} component="span" sx={typographySx}>
        {value || fallbackText}
      </Typography>
      {showEditButton && (
        <IconButton
          size="small"
          onClick={handleStart}
          sx={{
            padding: 0.5,
            color: "text.secondary",
            "&:hover": { color: "text.primary", backgroundColor: "action.hover" },
          }}
        >
          <EditIcon sx={{ fontSize: "1rem" }} />
        </IconButton>
      )}
    </Box>
  );
};
