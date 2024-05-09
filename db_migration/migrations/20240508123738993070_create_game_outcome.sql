CREATE TABLE game_outcome (
    user_id BIGINT NOT NULL,
    game_id INT NOT NULL,
    won BOOLEAN NOT NULL,
    tied BOOLEAN NOT NULL,
    CONSTRAINT pk_ids PRIMARY KEY (user_id, game_id),
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES discord_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_game_id FOREIGN KEY (game_id) REFERENCES game(id) ON DELETE CASCADE,
    CONSTRAINT one_outcome_check CHECK (NOT (won AND tied))
);