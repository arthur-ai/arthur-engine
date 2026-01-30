# Evaluator Selector Components - Migration Status

This directory contains evaluator selector components for `arthur-engine`. As part of the "Primitives and Small Chunks" migration strategy, the presentational UI components have been extracted to `@arthur/shared-components` while container components remain here.

## Migration Architecture

The evaluator selector components have been split into two categories:

### Container Components (Remain Here)

These components handle:

- **Data fetching** - Using `useEvals` and `useEvalVersions` hooks
- **State management** - Form state via `withFieldGroup`
- **API mutations** - Fetching eval details when adding evaluators
- **App-specific logic** - Variable mapping, form integration

**Container Components:**

- `evaluator-selector.tsx` - Container for `EvaluatorsSelectorUI` (used in agent-experiments and agent-notebook)

### Presentational Components (Migrated to shared-components)

These components have been moved to `@arthur/shared-components`:

- `EvaluatorsSelectorUI` - Pure UI component for selecting multiple evaluators
- `EvaluatorSelectorUI` - Pure UI component for selecting a single evaluator

## Current State

### Components Still in This Directory

**Container Components:**

- `evaluator-selector.tsx` - Thin container that:
  - Fetches evaluators and versions via hooks
  - Manages form state for `evals` array
  - Handles API mutation to fetch eval details
  - Renders `EvaluatorsSelectorUI` with all necessary props

**Temporary Presentational Components:**

- `EvaluatorsSelectorUI.tsx` - ⚠️ Will be removed - use `@arthur/shared-components`

### Import Strategy

Currently, components in this directory still use **local imports** for the presentational components. The migration plan is:

1. ✅ **Phase 1 (Complete)**: Extract presentational components to `shared-components`
2. ⏳ **Phase 2 (Future)**: Update imports in this directory to use `@arthur/shared-components`
3. ⏳ **Phase 3 (Future)**: Remove duplicate components from this directory

### Example: How Container Components Work

```tsx
// evaluator-selector.tsx (Container - stays here)
export const EvaluatorsSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals">,
  render: function Render({ group }) {
    // Data fetching
    const { evals } = useEvals(task?.id, { page: 0, pageSize: 100, sort: "desc" });
    const { versions } = useEvalVersions(task?.id, currentEvaluator.name ?? undefined, ...);

    // API mutation
    const addEval = useMutation({ ... });

    // Form state
    const selectedEvals = useStore(group.store, (state) => state.values.evals);

    // Render presentational component
    return (
      <EvaluatorsSelectorUI
        evaluators={evals}
        versions={versions}
        selectedEvaluator={selectedEvaluator}
        selectedVersion={selectedVersion}
        selectedEvals={selectedEvals}
        onSelectEvaluator={handleSelectEvaluator}
        onSelectVersion={handleSelectVersion}
        onAdd={handleAdd}
        onRemove={handleRemove}
        isAdding={addEval.isPending}
        error={errorMessage}
      />
    );
  },
});
```

## Component Dependencies

Container components in this directory depend on:

- `@tanstack/react-query` - Data fetching (`useMutation`)
- `@tanstack/react-form` - Form state management (`withFieldGroup`, `useStore`)
- `@/components/evaluators/hooks/useEvals` - Evaluator data fetching
- `@/components/evaluators/hooks/useEvalVersions` - Version data fetching
- `@/hooks/useApi` - API client
- `@/hooks/useTask` - Task context
- `@arthur/shared-components` - Presentational components (future)

## Migration Notes

### EvaluatorsSelector Migration

- The container component keeps all data fetching and form management
- The UI component is now pure and accepts all data/callbacks as props
- The same initialization behavior is maintained

### EvaluatorSelector Migration

- Similar pattern - container handles form state and data fetching
- UI component is pure and accepts props
- Used in live-evals forms

## Next Steps

1. ✅ Presentational components extracted to shared-components
2. ⏳ Update imports in container components to use `@arthur/shared-components`
3. ⏳ Remove duplicate presentational components from this directory
4. ⏳ Test that functionality remains unchanged after import migration

## File Structure

```
components/
├── evaluator-selector.tsx          # Container - fetches data, manages form, renders EvaluatorsSelectorUI
└── EvaluatorsSelectorUI.tsx        # ⚠️ Will be removed - use @arthur/shared-components
```

## Important Notes

- **Functionality Preservation**: The migration maintains the same user-facing functionality. Container components continue to work exactly as before, just with presentational components imported from shared-components.

- **No Breaking Changes**: The API of container components remains the same. Only internal implementation (imports) will change.

- **Testing**: After updating imports, thorough testing is needed to ensure:
  - Evaluator selection works
  - Version selection works
  - Add button works correctly
  - Error messages display properly
  - Remove functionality works
  - Form state is properly managed
