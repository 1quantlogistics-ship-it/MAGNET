/**
 * MAGNET UI Error Components
 *
 * Error boundary and display components.
 */

// Legacy exports (if they exist)
export {
  UIErrorBoundary,
  withErrorBoundary,
  useErrorBoundary,
} from './UIErrorBoundary';

export {
  ErrorDisplay,
  ErrorIndicator,
  LoadingFallback,
} from './ErrorDisplay';

// V1.4 Error Components
export { ErrorBoundary } from './ErrorBoundary';
export { ErrorOverlay } from './ErrorOverlay';
export { ErrorToast } from './ErrorToast';
export { StaleContentNotice } from './StaleContentNotice';
export { FallbackModal } from './FallbackModal';
export { ConnectionBanner } from './ConnectionBanner';
