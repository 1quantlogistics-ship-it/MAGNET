/**
 * MAGNET UI Module 02: PRS Components
 *
 * Prompt Recommendation System components index.
 * VisionOS-style contextual suggestions.
 */

// VisionSurface - Unified glass material
export {
  VisionSurface,
  BlurredVisionSurface,
  type VisionSurfaceProps,
} from './VisionSurface';

// ContextMenu - 3D-aware context menu
export {
  ContextMenu,
  type ContextMenuProps,
} from './ContextMenu';

// ContextMenuItem - Menu item components
export {
  ContextMenuItem,
  ContextMenuGroup,
  ContextMenuDivider,
  type ContextMenuItemProps,
} from './ContextMenuItem';

// PromptChip - Chat suggestion chips
export {
  PromptChip,
  PromptChipGroup,
  type PromptChipProps,
  type PromptChipGroupProps,
} from './PromptChip';

// Icons
export {
  PRSIcon,
  CategoryIcon,
  getCategoryIconName,
  type PRSIconProps,
  type PRSIconName,
} from './icons/PRSIcons';
