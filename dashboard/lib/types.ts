export type PersonaStatus = "draft" | "training" | "ready" | "failed";
export type SafetyStatus = "pending" | "passed" | "blocked";
export type ReviewStatus = "pending" | "approved" | "rejected";

export interface Persona {
  id: string;
  name: string;
  brand_voice: string;
  trigger_word: string;
  status: PersonaStatus;
  consent_attestation: boolean;
  likeness_lora_url: string;
}

export interface Content {
  id: string;
  persona_id: string;
  channel: string;
  kind: "image" | "video";
  safety_status: SafetyStatus;
  review_status: ReviewStatus;
  media_url: string | null;
  aspect_ratio: string;
  prompt: string;
}

export interface Product {
  id: string;
  name: string;
  category: string;
}
