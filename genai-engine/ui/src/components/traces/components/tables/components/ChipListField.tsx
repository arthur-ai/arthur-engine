import { Add, Close } from "@mui/icons-material";
import { Box, Chip, IconButton, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";

interface ChipListFieldProps {
  label: string;
  placeholder: string;
  values: string[];
  onAdd: (value: string) => void;
  onRemove: (value: string) => void;
}

export const ChipListField = ({ label, placeholder, values, onAdd, onRemove }: ChipListFieldProps) => {
  const [input, setInput] = useState("");

  const commit = () => {
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }
    onAdd(trimmed);
    setInput("");
  };

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        {label}
      </Typography>
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <TextField
          size="small"
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
          }}
          placeholder={placeholder}
          autoComplete="off"
          slotProps={{
            htmlInput: {
              "data-1p-ignore": true,
            },
          }}
        />
        <IconButton size="small" onClick={commit} disabled={!input.trim()} color="primary">
          <Add />
        </IconButton>
      </Stack>
      <Stack direction="row" flexWrap="wrap" gap={1}>
        {values.map((id) => (
          <Chip key={id} label={id} size="small" onDelete={() => onRemove(id)} deleteIcon={<Close />} />
        ))}
      </Stack>
    </Box>
  );
};
