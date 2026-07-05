CREATE TABLE IF NOT EXISTS tbl_catalysts (
  catalyst_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  state VARCHAR(15) NOT NULL,
  description VARCHAR,
  evidence JSON,
  enabled BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT catalysts_pkey PRIMARY KEY (catalyst_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id)
);

CREATE TABLE IF NOT EXISTS tbl_catalysts_history (
  catalyst_history_id VARCHAR(36) NOT NULL,
  catalyst_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  state VARCHAR(15) NOT NULL,
  description VARCHAR,
  evidence JSON,
  enabled BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT catalysts_history_pkey PRIMARY KEY (catalyst_history_id),
  CONSTRAINT catalysts_fkey FOREIGN KEY (catalyst_id) REFERENCES tbl_catalysts(catalyst_id)
);
