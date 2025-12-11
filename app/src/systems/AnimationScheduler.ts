/**
 * MAGNET UI Animation Scheduler
 *
 * Central animation lifecycle management for lifecycle-aware hooks.
 * FM4 Compliance: Prevents stale closures, handles cancellation, coordinates animations.
 */

import type { AnimationSchedulerContract } from '../types/contracts';
import { VISIONOS_TIMING } from '../types/common';

/**
 * Animation priority levels
 */
export type AnimationPriority = 'critical' | 'high' | 'normal' | 'low';

/**
 * Animation state
 */
export type AnimationState = 'pending' | 'running' | 'paused' | 'completed' | 'cancelled';

/**
 * Animation entry
 */
export interface AnimationEntry {
  id: string;
  name: string;
  priority: AnimationPriority;
  state: AnimationState;
  startTime: number;
  duration: number;
  progress: number;
  onUpdate: (progress: number, deltaTime: number) => void;
  onComplete?: () => void;
  onCancel?: () => void;
  easing?: (t: number) => number;
}

/**
 * Scheduler configuration
 */
interface SchedulerConfig {
  /** Target frame rate */
  targetFPS?: number;
  /** Maximum animations per frame */
  maxAnimationsPerFrame?: number;
  /** Enable debug logging */
  debug?: boolean;
  /** Auto-pause when tab is hidden */
  autoPauseOnHidden?: boolean;
}

/**
 * Priority order for sorting
 */
const PRIORITY_ORDER: Record<AnimationPriority, number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

/**
 * Common easing functions
 */
export const EASING = {
  linear: (t: number) => t,
  easeOut: (t: number) => 1 - Math.pow(1 - t, 3),
  easeIn: (t: number) => Math.pow(t, 3),
  easeInOut: (t: number) =>
    t < 0.5 ? 4 * Math.pow(t, 3) : 1 - Math.pow(-2 * t + 2, 3) / 2,
  spring: (t: number) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0
      ? 0
      : t === 1
        ? 1
        : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  },
};

/**
 * AnimationScheduler - Central animation lifecycle manager
 */
class AnimationScheduler implements AnimationSchedulerContract {
  private static instance: AnimationScheduler;
  private config: Required<SchedulerConfig>;

  private animations: Map<string, AnimationEntry> = new Map();
  private frameId: number | null = null;
  private lastFrameTime: number = 0;
  private isPaused: boolean = false;
  private frameCount: number = 0;

  // Performance tracking
  private frameTimes: number[] = [];
  private readonly maxFrameTimeSamples = 60;

  private constructor(config: SchedulerConfig = {}) {
    this.config = {
      targetFPS: config.targetFPS ?? 60,
      maxAnimationsPerFrame: config.maxAnimationsPerFrame ?? 50,
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      autoPauseOnHidden: config.autoPauseOnHidden ?? true,
    };

    this.setupVisibilityHandler();
  }

  /**
   * Get singleton instance
   */
  static getInstance(): AnimationScheduler {
    if (!AnimationScheduler.instance) {
      AnimationScheduler.instance = new AnimationScheduler();
    }
    return AnimationScheduler.instance;
  }

  /**
   * Setup visibility change handler
   */
  private setupVisibilityHandler(): void {
    if (typeof document === 'undefined') return;

    document.addEventListener('visibilitychange', () => {
      if (this.config.autoPauseOnHidden) {
        if (document.hidden) {
          this.pause();
        } else {
          this.resume();
        }
      }
    });
  }

  /**
   * Schedule a new animation
   */
  schedule(
    id: string,
    config: {
      name?: string;
      duration: number;
      priority?: AnimationPriority;
      onUpdate: (progress: number, deltaTime: number) => void;
      onComplete?: () => void;
      onCancel?: () => void;
      easing?: (t: number) => number;
    }
  ): string {
    // Cancel existing animation with same ID
    if (this.animations.has(id)) {
      this.cancel(id);
    }

    const entry: AnimationEntry = {
      id,
      name: config.name ?? id,
      priority: config.priority ?? 'normal',
      state: 'pending',
      startTime: 0,
      duration: config.duration,
      progress: 0,
      onUpdate: config.onUpdate,
      onComplete: config.onComplete,
      onCancel: config.onCancel,
      easing: config.easing ?? EASING.easeOut,
    };

    this.animations.set(id, entry);

    // Start the loop if not running
    if (this.frameId === null && !this.isPaused) {
      this.startLoop();
    }

    if (this.config.debug) {
      console.log(`[AnimationScheduler] Scheduled: ${id} (${config.duration}ms)`);
    }

    return id;
  }

  /**
   * Cancel an animation
   */
  cancel(id: string): void {
    const entry = this.animations.get(id);
    if (entry) {
      entry.state = 'cancelled';
      entry.onCancel?.();
      this.animations.delete(id);

      if (this.config.debug) {
        console.log(`[AnimationScheduler] Cancelled: ${id}`);
      }
    }
  }

  /**
   * Check if an animation is running
   */
  isRunning(id: string): boolean {
    const entry = this.animations.get(id);
    return entry?.state === 'running' || entry?.state === 'pending';
  }

  /**
   * Get animation progress (0-1)
   */
  getProgress(id: string): number {
    return this.animations.get(id)?.progress ?? 0;
  }

  /**
   * Pause all animations
   */
  pause(): void {
    this.isPaused = true;
    if (this.frameId !== null) {
      cancelAnimationFrame(this.frameId);
      this.frameId = null;
    }

    // Mark all running animations as paused
    for (const entry of this.animations.values()) {
      if (entry.state === 'running') {
        entry.state = 'paused';
      }
    }

    if (this.config.debug) {
      console.log('[AnimationScheduler] Paused');
    }
  }

  /**
   * Resume all animations
   */
  resume(): void {
    if (!this.isPaused) return;

    this.isPaused = false;

    // Mark all paused animations as running
    for (const entry of this.animations.values()) {
      if (entry.state === 'paused') {
        entry.state = 'running';
      }
    }

    // Restart the loop if we have animations
    if (this.animations.size > 0) {
      this.lastFrameTime = performance.now();
      this.startLoop();
    }

    if (this.config.debug) {
      console.log('[AnimationScheduler] Resumed');
    }
  }

  /**
   * Cancel all animations
   */
  cancelAll(): void {
    for (const entry of this.animations.values()) {
      entry.state = 'cancelled';
      entry.onCancel?.();
    }
    this.animations.clear();

    if (this.frameId !== null) {
      cancelAnimationFrame(this.frameId);
      this.frameId = null;
    }

    if (this.config.debug) {
      console.log('[AnimationScheduler] All animations cancelled');
    }
  }

  /**
   * Start the animation loop
   */
  private startLoop(): void {
    this.lastFrameTime = performance.now();
    this.tick(this.lastFrameTime);
  }

  /**
   * Animation loop tick
   */
  private tick = (currentTime: number): void => {
    if (this.isPaused) return;

    const deltaTime = currentTime - this.lastFrameTime;
    this.lastFrameTime = currentTime;
    this.frameCount++;

    // Track frame time for performance monitoring
    this.frameTimes.push(deltaTime);
    if (this.frameTimes.length > this.maxFrameTimeSamples) {
      this.frameTimes.shift();
    }

    // Process animations sorted by priority
    const sortedAnimations = Array.from(this.animations.values())
      .filter((a) => a.state !== 'completed' && a.state !== 'cancelled')
      .sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
      .slice(0, this.config.maxAnimationsPerFrame);

    const completedIds: string[] = [];

    for (const entry of sortedAnimations) {
      // Initialize start time for pending animations
      if (entry.state === 'pending') {
        entry.state = 'running';
        entry.startTime = currentTime;
      }

      // Calculate progress
      const elapsed = currentTime - entry.startTime;
      const rawProgress = Math.min(elapsed / entry.duration, 1);
      const easedProgress = entry.easing?.(rawProgress) ?? rawProgress;

      entry.progress = easedProgress;

      // Call update handler
      try {
        entry.onUpdate(easedProgress, deltaTime);
      } catch (error) {
        console.error(`[AnimationScheduler] Update error for ${entry.id}:`, error);
      }

      // Check completion
      if (rawProgress >= 1) {
        entry.state = 'completed';
        completedIds.push(entry.id);
      }
    }

    // Handle completions
    for (const id of completedIds) {
      const entry = this.animations.get(id);
      if (entry) {
        try {
          entry.onComplete?.();
        } catch (error) {
          console.error(`[AnimationScheduler] Complete error for ${id}:`, error);
        }
        this.animations.delete(id);

        if (this.config.debug) {
          console.log(`[AnimationScheduler] Completed: ${id}`);
        }
      }
    }

    // Continue loop if we have animations
    if (this.animations.size > 0) {
      this.frameId = requestAnimationFrame(this.tick);
    } else {
      this.frameId = null;
    }
  };

  /**
   * Get current FPS
   */
  getCurrentFPS(): number {
    if (this.frameTimes.length === 0) return 0;

    const avgFrameTime =
      this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
    return Math.round(1000 / avgFrameTime);
  }

  /**
   * Get scheduler status
   */
  getStatus(): {
    animationCount: number;
    isPaused: boolean;
    fps: number;
    frameCount: number;
  } {
    return {
      animationCount: this.animations.size,
      isPaused: this.isPaused,
      fps: this.getCurrentFPS(),
      frameCount: this.frameCount,
    };
  }

  /**
   * Get all active animation IDs
   */
  getActiveAnimationIds(): string[] {
    return Array.from(this.animations.values())
      .filter((a) => a.state === 'running' || a.state === 'pending')
      .map((a) => a.id);
  }
}

/**
 * Export singleton instance
 */
export const animationScheduler = AnimationScheduler.getInstance();

/**
 * Helper: Schedule a spring animation
 */
export function scheduleSpring(
  id: string,
  config: {
    from: number;
    to: number;
    onUpdate: (value: number) => void;
    onComplete?: () => void;
    duration?: number;
  }
): string {
  const { from, to, onUpdate, onComplete, duration = VISIONOS_TIMING.panelEnter } = config;
  const range = to - from;

  return animationScheduler.schedule(id, {
    duration,
    easing: EASING.spring,
    onUpdate: (progress) => {
      onUpdate(from + range * progress);
    },
    onComplete,
  });
}

/**
 * Helper: Schedule a fade animation
 */
export function scheduleFade(
  id: string,
  config: {
    from: number;
    to: number;
    onUpdate: (opacity: number) => void;
    onComplete?: () => void;
    duration?: number;
  }
): string {
  const { from, to, onUpdate, onComplete, duration = VISIONOS_TIMING.tooltipReveal } = config;
  const range = to - from;

  return animationScheduler.schedule(id, {
    duration,
    easing: EASING.easeOut,
    onUpdate: (progress) => {
      onUpdate(from + range * progress);
    },
    onComplete,
  });
}

/**
 * Helper: Schedule a transform animation
 */
export function scheduleTransform(
  id: string,
  config: {
    from: { x?: number; y?: number; z?: number; scale?: number; rotate?: number };
    to: { x?: number; y?: number; z?: number; scale?: number; rotate?: number };
    onUpdate: (transform: { x: number; y: number; z: number; scale: number; rotate: number }) => void;
    onComplete?: () => void;
    duration?: number;
  }
): string {
  const {
    from,
    to,
    onUpdate,
    onComplete,
    duration = VISIONOS_TIMING.cardExpand,
  } = config;

  const fromX = from.x ?? 0;
  const fromY = from.y ?? 0;
  const fromZ = from.z ?? 0;
  const fromScale = from.scale ?? 1;
  const fromRotate = from.rotate ?? 0;

  const toX = to.x ?? fromX;
  const toY = to.y ?? fromY;
  const toZ = to.z ?? fromZ;
  const toScale = to.scale ?? fromScale;
  const toRotate = to.rotate ?? fromRotate;

  return animationScheduler.schedule(id, {
    duration,
    easing: EASING.spring,
    onUpdate: (progress) => {
      onUpdate({
        x: fromX + (toX - fromX) * progress,
        y: fromY + (toY - fromY) * progress,
        z: fromZ + (toZ - fromZ) * progress,
        scale: fromScale + (toScale - fromScale) * progress,
        rotate: fromRotate + (toRotate - fromRotate) * progress,
      });
    },
    onComplete,
  });
}

export { AnimationScheduler };
