CREATE TABLE discord_user (
    id BIGINT PRIMARY KEY,
    subscription_start_date TIMESTAMP,
    subscription_end_date TIMESTAMP,
    date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT start_before_end CHECK (subscription_start_date < subscription_end_date),
    CONSTRAINT start_end_xor CHECK ((subscription_start_date IS NULL) = (subscription_end_date IS NULL))
);