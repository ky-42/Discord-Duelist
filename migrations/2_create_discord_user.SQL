CREATE TABLE discord_user (
    id BIGINT PRIMARY KEY,
    subscription_start_date TIMESTAMP,
    subscription_end_date TIMESTAMP,
    CONSTRAINT start_before_end CHECK (subscription_start_date < subscription_end_date)
);