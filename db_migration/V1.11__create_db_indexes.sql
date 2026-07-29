-- Theses Proposals
CREATE INDEX idx_theses_proposals_user_id ON tbl_theses_proposals(user_id);

-- Quant Proposals
CREATE INDEX idx_quant_proposals_theses_id ON tbl_quant_proposals(theses_id);
CREATE INDEX idx_quant_proposals_theses_id_status ON tbl_quant_proposals(theses_id, quant_proposal_status);

-- Catalyst Proposals
CREATE INDEX idx_catalyst_proposals_theses_id ON tbl_catalyst_proposals(theses_id);
CREATE INDEX idx_catalyst_proposals_theses_id_status ON tbl_catalyst_proposals(theses_id, catalyst_proposal_status);

-- Evaluations
CREATE INDEX idx_evaluations_theses_id ON tbl_evaluations(theses_id);
CREATE INDEX idx_evaluations_theses_id_status ON tbl_evaluations(theses_id, evaluation_status);

-- Alerts Table
CREATE INDEX idx_alerts_user_id ON tbl_alerts(user_id);

-- Theses
CREATE INDEX idx_theses_user_id ON tbl_theses(user_id);

-- Quant Conditions
CREATE INDEX idx_quant_conditions_theses_id ON tbl_quant_conditions(theses_id);

-- Catalysts
CREATE INDEX idx_catalysts_theses_id ON tbl_catalysts(theses_id);

-- Outcomes
CREATE INDEX idx_outcomes_theses_id ON tbl_outcomes(theses_id);