CREATE TABLE IF NOT EXISTS tbl_quant_conditions (
  quant_condition_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  metric VARCHAR(36) NOT NULL,
  operator VARCHAR(2) NOT NULL,
  "value" DECIMAL NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT quant_conditions_pkey PRIMARY KEY (quant_condition_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id)
);

CREATE TABLE IF NOT EXISTS tbl_quant_conditions_history (
  quant_condition_history_id VARCHAR(36) NOT NULL,
  quant_condition_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  metric VARCHAR(36) NOT NULL,
  operator VARCHAR(2) NOT NULL,
  "value" DECIMAL NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT quant_conditions_history_pkey PRIMARY KEY (quant_condition_history_id),
  CONSTRAINT quant_conditions_fkey FOREIGN KEY (quant_condition_id) REFERENCES tbl_quant_conditions(quant_condition_id)
);
