export type Confidence = "high" | "medium" | "low";
export type Source = "input" | "inferred" | "llm";
export type Severity = "info" | "warning" | "error";

export type SortColumn = "classpath" | "confidence" | "status";
export type SortState = { column: SortColumn; direction: "asc" | "desc" } | null;

export interface EnrichedField {
  value: string;
  confidence: Confidence;
  source: Source;
  rationale: string;
}

export interface Attribute {
  label: string;
  value: string;
  uom: string | null;
  confidence: Confidence;
  source: Source;
  rationale: string;
  lov_compliant: boolean | null;
}

export interface ValidationFlag {
  field: string;
  issue: string;
  severity: Severity;
}

export interface EnrichedProduct {
  id: number;
  raw_mfg_part_num: string;
  raw_part_desc: string;
  raw_part_manuf: string;

  manufacturer_name: EnrichedField;
  brand_name: EnrichedField;
  classpath: EnrichedField;

  invoice_desc: EnrichedField;
  mobile_desc: EnrichedField;
  short_desc: EnrichedField;
  long_desc: EnrichedField;

  attributes: Attribute[];

  validation_flags: ValidationFlag[];
  status: "pending" | "reviewed";
  created_at: string;
}

export interface RawProductIn {
  mfg_part_num: string;
  part_desc: string;
  e1_brand?: string;
  unilog_brand?: string;
  dib_brand?: string;
  part_manuf: string;
}

export interface ProductPatch {
  manufacturer_name?: string;
  brand_name?: string;
  classpath?: string;
  invoice_desc?: string;
  mobile_desc?: string;
  short_desc?: string;
  long_desc?: string;
  attributes?: Record<string, string>;
  status?: string;
}

export interface Metrics {
  total: number;
  classification_confidence?: Record<Confidence, number>;
  attributes?: {
    total: number;
    from_input: number;
    from_input_pct: number;
  };
  lov_compliance?: {
    checked: number;
    compliant: number;
    compliant_pct: number;
  };
  char_limit_compliance?: {
    invoice_desc_ok_pct: number;
    mobile_desc_ok_pct: number;
  };
  dedup_flags?: number;
  needs_review?: number;
  needs_review_pct?: number;
  review_status?: {
    reviewed: number;
    auto_approved: number;
    manually_approved: number;
    pending: number;
    auto_approved_pct: number;
  };
  llm?: {
    backend: string;
    model: string;
    long_desc_generated: number;
    long_desc_generated_pct: number;
    fallback_classifications: number;
    llm_unreachable_count: number;
  };
}

export interface Evaluation {
  rows_scored: number;
  rows_in_ground_truth: number;
  overall: { fields_compared: number; exact_pct: number; any_match_pct: number };
  by_field: Record<
    string,
    { compared: number; exact_pct: number; any_match_pct: number; examples: { mpn: string; expected: string; got: string }[] }
  >;
  char_limit_compliance: Record<string, { within_limit: number; of: number; pct: number }>;
  attainable_ceiling: {
    ground_truth_attributes: number;
    present_in_raw_input: number;
    requires_manufacturer_source: number;
    reachable_pct: number;
    note: string;
    examples_requiring_external_source: string[];
  };
}
