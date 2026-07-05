CREATE TABLE IF NOT EXISTS tbl_stocks (
  stock_id VARCHAR(36) NOT NULL,
  ticker VARCHAR(30) NOT NULL UNIQUE,
  stock_status VARCHAR(10) NOT NULL,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT stocks_pkey PRIMARY KEY (stock_id)
);

CREATE TABLE IF NOT EXISTS tbl_stocks_history (
  stock_history_id VARCHAR(36) NOT NULL,
  stock_id VARCHAR(36) NOT NULL,
  ticker VARCHAR(30) NOT NULL,
  stock_status VARCHAR(10) NOT NULL,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT stocks_history_pkey PRIMARY KEY (stock_history_id),
  CONSTRAINT stocks_fkey FOREIGN KEY (stock_id) REFERENCES tbl_stocks(stock_id)
);
