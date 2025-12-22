# React Query Implementation Guide

## Overview

This directory contains standardized utilities for data fetching using React Query in Morphio. All data fetching should use these patterns to ensure consistency, caching, and optimal performance.

## Key Files

- `query-provider.tsx` - Provider component that wraps the application
- `query-keys.ts` - Centralized query key factory for consistent key structure
- `query-hooks.ts` - Base hooks with standardized error handling

## Usage Guidelines

### 1. Query Keys

Always use the `queryKeys` object from `query-keys.ts` to create query keys. This ensures consistent caching and invalidation.

```typescript
// Good
const { data } = useQuery({
  queryKey: queryKeys.templates.all,
  // ...
});

// Avoid
const { data } = useQuery({
  queryKey: ['templates'],
  // ...
});
```

### 2. Error Handling

Use the `useApiQuery` hook for standard API requests that return our API response format.

```typescript
import { useApiQuery } from '@/lib/react-query/query-hooks';

// This handles API-specific error responses
const { data } = useApiQuery(queryKeys.templates.all, getTemplates);
```

### 3. Creating New Query Hooks

When creating new query hooks:

1. Place them in `src/hooks/` with a name format of `use[Resource]Query.ts`
2. Import base utilities from `@/lib/react-query/`
3. Return a standardized interface: `{ data, isLoading, error, refetch }`
4. Use `'use client';` directive at the top

### 4. Migration Strategy

When migrating existing hooks:

1. Create a new version with `-query` suffix
2. Update components to use the new hook
3. Once all components are migrated, remove the old hook

## Example Hooks

- `useTemplatesQuery.ts` - Example of a basic query hook
- `useSavedContentsQuery.ts` - Example with dependent queries
- `useJobStatusQuery.ts` - Example with polling
