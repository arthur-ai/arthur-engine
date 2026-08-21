import { Add, Close } from "@mui/icons-material";
import { Box, Chip, IconButton, Stack, TextField, Typography } from "@mui/material";

interface ChipListFieldProps {
  label: string;
  placeholder: string;
  values: string[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onAdd: (value: string) => void;
  onRemove: (value: string) => void;
}

export const ChipListField = ({ label, placeholder, values, inputValue, onInputChange, onAdd, onRemove }: ChipListFieldProps) => {
  const commit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    onAdd(trimmed);
    onInputChange("");
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
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit(inputValue);
            }
          }}
          onPaste={(e) => {
            const pastedText = e.clipboardData.getData("text").trim();
            if (pastedText) {
              e.preventDefault();
              commit(pastedText);
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
        <IconButton size="small" onClick={() => commit(inputValue)} disabled={!inputValue.trim()} color="primary">
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
