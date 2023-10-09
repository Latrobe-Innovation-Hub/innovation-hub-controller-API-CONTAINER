-- schema.sql

-- Create the Host table
CREATE TABLE IF NOT EXISTS Host (
    id INTEGER PRIMARY KEY,
    host_address TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);