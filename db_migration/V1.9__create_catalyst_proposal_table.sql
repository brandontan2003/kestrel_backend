CREATE TABLE IF NOT EXISTS tbl_catalyst_proposals (
  catalyst_proposal_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,

  catalyst_id VARCHAR(36), -- NULL when proposal_type = 'add' (no existing row yet).
  proposal_type VARCHAR(15) NOT NULL, -- add | remove (update 'enabled' to False) | update

  proposed_change JSON NOT NULL,
  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36),

  catalyst_proposal_status VARCHAR(15) NOT NULL,  -- pending | approved | rejected | superseded
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT catalyst_proposals_pkey PRIMARY KEY (catalyst_proposal_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id),
  CONSTRAINT catalyst_fkey FOREIGN KEY (catalyst_id) REFERENCES tbl_catalysts(catalyst_id),
  CONSTRAINT evaluation_fkey FOREIGN KEY (source_evaluation_id) REFERENCES tbl_evaluations(evaluation_id)
);

CREATE TABLE IF NOT EXISTS tbl_catalyst_proposals_history (
  catalyst_proposal_history_id VARCHAR(36) NOT NULL,
  catalyst_proposal_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,

  catalyst_id VARCHAR(36),
  proposal_type VARCHAR(15) NOT NULL,

  proposed_change JSON NOT NULL,
  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36),

  catalyst_proposal_status VARCHAR(15) NOT NULL,
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT catalyst_proposals_history_pkey PRIMARY KEY (catalyst_proposal_history_id),
  CONSTRAINT catalyst_proposals_fkey FOREIGN KEY (catalyst_proposal_id) REFERENCES tbl_catalyst_proposals(catalyst_proposal_id)
);