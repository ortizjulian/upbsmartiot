CREATE TABLE predicciones_temp (
    id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255),
    time_index TIMESTAMP,
    temp FLOAT
);

CREATE TABLE predicciones_humedad (
    id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255),
    time_index TIMESTAMP,
    humedad FLOAT
);
