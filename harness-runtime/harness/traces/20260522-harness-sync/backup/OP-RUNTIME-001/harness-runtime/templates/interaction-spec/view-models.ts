/**
 * UI-only contracts for interaction design.
 * These types describe screen state and form/view models; they do not define
 * backend APIs, persistence, transport, or database shape.
 */

export type InteractionState =
  | "loading"
  | "empty"
  | "success"
  | "error"
  | "permission_denied"
  | "disabled";

export interface ScreenViewModel {
  screenId: string;
  state: InteractionState;
  primaryDomainObjectIds: string[];
  visibleActions: string[];
  disabledActions: Array<{
    action: string;
    reason: string;
  }>;
  messages: Array<{
    kind: "empty" | "error" | "success" | "warning" | "info";
    text: string;
    traceRef: string;
  }>;
}

export interface FormViewModel {
  formId: string;
  fields: Array<{
    name: string;
    label: string;
    required: boolean;
    valueState: "pristine" | "dirty" | "valid" | "invalid";
    errorMessage?: string;
    traceRef: string;
  }>;
}

