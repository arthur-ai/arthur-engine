/**
 * Threshold for considering an evaluation score a "pass".
 * Intentional cross-language mirror of `EVAL_PASS_THRESHOLD` in
 * genai-engine/src/utils/constants.py, which the experiment executors use to
 * compute aggregate pass counts (score >= threshold, 0-1 scale).
 * Keep the two values in sync.
 */
export const EVAL_PASS_THRESHOLD = 0.5;

/** Whether an eval score counts as a pass. Centralized so UI matches the backend. */
export const isEvalPass = (score: number): boolean => score >= EVAL_PASS_THRESHOLD;
