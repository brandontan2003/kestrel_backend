CREATE TABLE IF NOT EXISTS tbl_quant_proposals (
  quant_proposal_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  quant_condition_id VARCHAR(36) NOT NULL, -- the condition being changed
  proposed_change JSON NOT NULL,

  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36) NOT NULL,

  quant_proposal_status VARCHAR(15) NOT NULL, -- pending | approved | rejected | superseded
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT quant_proposals_pkey PRIMARY KEY (quant_proposal_id),
  CONSTRAINT quant_proposals_theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id),
  CONSTRAINT quant_proposals_condition_fkey FOREIGN KEY (quant_condition_id) REFERENCES tbl_quant_conditions(quant_condition_id),
  CONSTRAINT quant_proposals_evaluation_fkey FOREIGN KEY (source_evaluation_id) REFERENCES tbl_evaluations(evaluation_id)
);

CREATE TABLE IF NOT EXISTS tbl_quant_proposals_history (
  quant_proposal_history_id VARCHAR(36) NOT NULL,
  quant_proposal_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  quant_condition_id VARCHAR(36) NOT NULL,
  proposed_change JSON NOT NULL,

  llm_rationale TEXT,
  llm_confidence DECIMAL(4, 3),

  source_article_url TEXT,
  source_evaluation_id VARCHAR(36)  NOT NULL,

  quant_proposal_status VARCHAR(15) NOT NULL,
  rejection_reason TEXT,
  resolved_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT quant_proposals_history_pkey PRIMARY KEY (quant_proposal_id),
  CONSTRAINT quant_proposals_fkey FOREIGN KEY (quant_proposal_id) REFERENCES tbl_quant_proposals(quant_proposal_id)
);
