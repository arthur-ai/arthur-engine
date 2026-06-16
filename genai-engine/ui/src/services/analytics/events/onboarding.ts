type FormVariant = "linear" | "wizard";
type WizardStepName = "identity" | "about" | "discovery";

export interface OnboardingEvents {
  "onboarding/api_key_clicked": { task_id: string; source: "traces_welcome" };
  "onboarding/task_id_copied": { task_id: string; source: "traces_welcome" };
  "onboarding/view_traces_clicked": { task_id: string; source: "traces_welcome" };
  "onboarding/skip_setup_clicked": { task_id: string; source: "traces_welcome" };
  "onboarding/landing_viewed": undefined;
  "onboarding/path_selected": { path: "try" | "login" };
  "onboarding/form_viewed": { variant: FormVariant };
  "onboarding/form_started": { variant: FormVariant };
  "onboarding/form_back_clicked": { variant: FormVariant };
  "onboarding/form_submit_failed": { variant: FormVariant; invalid_fields?: string[]; message?: string };
  // Keys are camelCase on the wire today — do not snake_case them.
  "onboarding/form_submitted": {
    variant: FormVariant;
    maturity: string;
    brings: string;
    bringsOther: string;
    competitors: string[];
    competitorOther: string;
    attribution: string;
    attributionOther: string;
    company: string;
  };
  "onboarding/login_viewed": undefined;
  "onboarding/wizard_step_viewed": { step: number; step_name: WizardStepName };
  "onboarding/wizard_step_completed": { step: number; step_name: WizardStepName };
  "onboarding/wizard_step_submit_failed": { step: number; step_name: WizardStepName; invalid_fields: string[] };
  "onboarding/wizard_step_back": { from_step: number; to_step: number };
  "onboarding/wizard_certificate_viewed": { course: string };
  "onboarding/wizard_certificate_share_clicked": { destination: "linkedin" | "x"; course: string };
  "onboarding/wizard_certificate_download_clicked": { course: string };
  "onboarding/wizard_certificate_closed": { method: "continue" | "dismiss"; course: string };
  "onboarding/wizard_cta_viewed": { course: string };
  "onboarding/wizard_cta_book_clicked": { course: string };
}
