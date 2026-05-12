import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm'],
  target: 'node20',
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
});
