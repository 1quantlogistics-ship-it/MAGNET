/**
 * MAGNET UI Schema Version
 *
 * Central version tracking for UI state schemas.
 * All types that sync with backend must include schema_version.
 * Increment on breaking changes to ensure reconciliation compatibility.
 */

export const UI_SCHEMA_VERSION = '1.0.0' as const;

/** Alias for backwards compatibility */
export const SCHEMA_VERSION = UI_SCHEMA_VERSION;

export type UISchemaVersion = typeof UI_SCHEMA_VERSION;

/**
 * Version metadata for schema evolution tracking
 */
export interface SchemaVersionMeta {
  version: UISchemaVersion;
  compatibleWith: string[];  // Previous versions this can reconcile from
  breakingChanges?: string[];
}

export const SCHEMA_META: SchemaVersionMeta = {
  version: UI_SCHEMA_VERSION,
  compatibleWith: [],
  breakingChanges: [
    'Initial schema - no prior versions'
  ]
};

/**
 * Type guard to check schema version compatibility
 */
export function isCompatibleVersion(version: string): version is UISchemaVersion {
  return version === UI_SCHEMA_VERSION || SCHEMA_META.compatibleWith.includes(version);
}
