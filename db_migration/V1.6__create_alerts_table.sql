CREATE TABLE IF NOT EXISTS tbl_alerts (
  alert_id VARCHAR(36) NOT NULL,
  evaluation_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  channels_sent VARCHAR(10) NOT NULL,
  alert_status VARCHAR(15) NOT NULL, -- NOT_SENT, SENT, IN_PROGRESS

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT alerts_pkey PRIMARY KEY (alert_id),
  CONSTRAINT evaluation_id_fkey FOREIGN KEY (evaluation_id) REFERENCES tbl_evaluations(evaluation_id),
  CONSTRAINT user_fkey FOREIGN KEY (user_id) REFERENCES tbl_users(user_id)
);

CREATE TABLE IF NOT EXISTS tbl_alerts_history (
  alert_history_id VARCHAR(36) NOT NULL,
  alert_id VARCHAR(36) NOT NULL,
  evaluation_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  channels_sent VARCHAR(10) NOT NULL,
  alert_status VARCHAR(15) NOT NULL, -- NOT_SENT, SENT, IN_PROGRESS

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT alerts_history_pkey PRIMARY KEY (alert_history_id),
  CONSTRAINT alerts_fkey FOREIGN KEY (alert_id) REFERENCES tbl_alerts(alert_id)
);
