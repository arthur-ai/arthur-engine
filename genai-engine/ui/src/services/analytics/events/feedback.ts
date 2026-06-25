type FeedbackType = "positive" | "negative" | null;

export interface FeedbackEvents {
  "feedback/opened": { trace_id: string; feedback_type: FeedbackType };
  "feedback/submitted": { trace_id: string; feedback_type: FeedbackType; details_length: number; success: boolean };
  "feedback/cleared": { trace_id: string };
  "feedback/error": { trace_id: string; error_message: string; feedback_type?: FeedbackType };
}
