CREATE TABLE game (
    id SERIAL PRIMARY KEY,
    game_type VARCHAR(255) NOT NULL,
    end_date TIMESTAMP NOT NULL
);