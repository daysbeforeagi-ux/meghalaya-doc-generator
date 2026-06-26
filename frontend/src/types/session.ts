export type DocType = "speech" | "press_release";
export type SpeakerRole = "cm" | "governor" | "deputy_cm" | "other";
export type LengthTarget =
  | "100-150"
  | "150-500"
  | "500-750"
  | "750-1250"
  | "1250+"
  | "quality-based";
export type SessionStatus =
  | "intake"
  | "researching"
  | "drafting"
  | "review"
  | "done"
  | "error";

export interface SessionPublic {
  session_id: string;
  status: SessionStatus;
  doc_type: DocType | null;
  brief: string | null;
  length_target: LengthTarget | null;
  error_message: string | null;
  deliverable_ready: boolean;
  dossier_ready: boolean;
}

export interface IntakePayload {
  doc_type?: DocType;
  speaker_role?: SpeakerRole;
  speaker_name?: string;
  use_pictures?: boolean;
  brief?: string;
  length_target?: LengthTarget;
}
