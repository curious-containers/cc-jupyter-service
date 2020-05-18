DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;
DROP TABLE IF EXISTS notebook;
DROP TABLE IF EXISTS experiment;
DROP TABLE IF EXISTS cookie;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agency_username TEXT NOT NULL,
  agency_url TEXT NOT NULL
);

CREATE TABLE notebook (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  notebook_id TEXT UNIQUE NOT NULL,
  notebook_token TEXT UNIQUE NOT NULL,
  experiment_id TEXT NOT NULL,
  status INTEGER NOT NULL,  -- 0: processing   1: succeeded   2: failed
  notebook_filename TEXT NOT NULL,
  user_id INTEGER,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE cookie (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cookie_text TEXT NOT NULL,
  creation_time REAL NOT NULL,
  user_id INTEGER,
  FOREIGN KEY (user_id) REFERENCES user (id)
);
