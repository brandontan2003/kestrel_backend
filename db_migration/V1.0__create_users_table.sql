CREATE TABLE IF NOT EXISTS tbl_users (
  user_id VARCHAR(36) NOT NULL,
  email VARCHAR NOT NULL UNIQUE,
  username VARCHAR NOT NULL,
  user_status VARCHAR(10) NOT NULL,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (user_id),
);


CREATE TABLE IF NOT EXISTS tbl_users_history (
  user_history_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  email VARCHAR NOT NULL UNIQUE,
  username VARCHAR NOT NULL,
  user_status VARCHAR(10) NOT NULL,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CONSTRAINT users_history_pkey PRIMARY KEY (user_history_id),
  CONSTRAINT user_id_fkey FOREIGN KEY (user_id) REFERENCES tbl_users(user_id)
);
