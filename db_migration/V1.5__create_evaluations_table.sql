CREATE TABLE IF NOT EXISTS tbl_evaluations (
  evaluation_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  state VARCHAR(15) NOT NULL,
  prompt_version VARCHAR NOT NULL,
  results JSON,
  signal BOOLEAN NOT NULL DEFAULT TRUE,
  reason VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT evaluations_pkey PRIMARY KEY(evaluation_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id)
);

CREATE TABLE IF NOT EXISTS tbl_evaluations_history (
  evaluation_history_id VARCHAR(36) NOT NULL,
  evaluation_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  state VARCHAR(15) NOT NULL,
  prompt_version VARCHAR NOT NULL,
  results JSON,
  signal BOOLEAN NOT NULL DEFAULT TRUE,
  reason VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT evaluations_history_pkey PRIMARY KEY(evaluation_history_id),
  CONSTRAINT evaluations_fkey FOREIGN KEY (evaluation_id) REFERENCES tbl_evaluations(evaluation_id)
);
