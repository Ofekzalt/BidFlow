CREATE USER authentication WITH PASSWORD 'authentication';
CREATE USER auction WITH PASSWORD 'auction';
CREATE USER settlement WITH PASSWORD 'settlement';

CREATE DATABASE authentication OWNER authentication;
CREATE DATABASE auction OWNER auction;
CREATE DATABASE settlement OWNER settlement;

GRANT ALL PRIVILEGES ON DATABASE authentication TO authentication;
GRANT ALL PRIVILEGES ON DATABASE auction TO auction;
GRANT ALL PRIVILEGES ON DATABASE settlement TO settlement;
