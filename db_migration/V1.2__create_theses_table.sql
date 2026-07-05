CREATE TABLE IF NOT EXISTS tbl_theses (
  theses_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  stock_id VARCHAR(36) NOT NULL,
  theses_status VARCHAR(10) NOT NULL,
  quant_mode VARCHAR(5) NOT NULL, -- To store all|any
  catalyst_mode VARCHAR(15) NOT NULL, -- To store all|any|none_required
  notes VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT theses_pkey PRIMARY KEY (theses_id),
  CONSTRAINT user_fkey FOREIGN KEY (user_id) REFERENCES tbl_users(user_id),
  CONSTRAINT stock_fkey FOREIGN KEY (stock_id) REFERENCES tbl_stocks(stock_id)
);

CREATE TABLE IF NOT EXISTS tbl_theses_history (
  theses_history_id VARCHAR(36) NOT NULL,
  theses_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  stock_id VARCHAR(36) NOT NULL,
  theses_status VARCHAR(10) NOT NULL,
  quant_mode VARCHAR(5) NOT NULL,
  catalyst_mode VARCHAR(15) NOT NULL,
  notes VARCHAR,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT theses_history_pkey PRIMARY KEY (theses_history_id),
  CONSTRAINT theses_fkey FOREIGN KEY (theses_id) REFERENCES tbl_theses(theses_id)
);
