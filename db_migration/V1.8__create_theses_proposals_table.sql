CREATE TABLE IF NOT EXISTS tbl_theses_proposals (
  theses_proposal_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  stock_id VARCHAR(36) NOT NULL,
  proposed_change JSON NOT NULL,

  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36) NOT NULL,
  theses_proposal_status VARCHAR(15) NOT NULL, -- pending | approved | rejected | superseded
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT theses_proposals_pkey PRIMARY KEY (theses_proposal_id),
  CONSTRAINT user_fkey FOREIGN KEY (user_id) REFERENCES tbl_users(user_id),
  CONSTRAINT stock_fkey FOREIGN KEY (stock_id) REFERENCES tbl_stocks(stock_id),
  CONSTRAINT evaluation_fkey FOREIGN KEY (source_evaluation_id) REFERENCES tbl_evaluations(evaluation_id)
);

CREATE TABLE IF NOT EXISTS tbl_theses_proposals_history (
  theses_proposal_history_id VARCHAR(36) NOT NULL,
  theses_proposal_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  stock_id VARCHAR(36) NOT NULL,
  proposed_change JSON NOT NULL,

  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36) NOT NULL,
  theses_proposal_status VARCHAR(15) NOT NULL,
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT theses_proposals_history_pkey PRIMARY KEY (theses_proposal_history_id),
  CONSTRAINT theses_proposal_fkey FOREIGN KEY (theses_proposal_id) REFERENCES tbl_theses_proposals(theses_proposal_id)
);
