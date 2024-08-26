CREATE ROLE inbox WITH LOGIN PASSWORD 'password';
ALTER USER inbox WITH superuser;
CREATE DATABASE inbox;
ALTER ROLE inbox SET client_encoding TO 'utf8';
ALTER ROLE inbox SET default_transaction_isolation TO 'read committed';
ALTER ROLE inbox SET timezone TO 'UTC';
ALTER USER inbox CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE inbox TO inbox;