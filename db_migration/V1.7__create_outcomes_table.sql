CREATE TABLE IF NOT EXISTS tbl_outcomes (
  outcome_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  price_at_signal MONEY NOT NULL,
  llm_confidence DECIMAL(4, 3) NOT NULL,
  triggered_at TIMESTAMP,
  price_after_30d MONEY,
  notes VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT outcomes_pkey PRIMARY KEY (outcome_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id)
);

CREATE TABLE IF NOT EXISTS tbl_outcomes_history (
  outcome_history_id VARCHAR(36) NOT NULL,
  outcome_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  price_at_signal MONEY NOT NULL,
  llm_confidence DECIMAL(4, 3) NOT NULL,
  triggered_at TIMESTAMP,
  price_after_30d MONEY,
  notes VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT outcomes_history_pkey PRIMARY KEY (outcome_history_id),
  CONSTRAINT outcome_fkey FOREIGN KEY (outcome_id) REFERENCES tbl_outcomes(outcome_id)
);