-- 华老师导读强化应用 · 初始 schema
-- 在 Neon SQL Editor 第一次执行

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id TEXT NOT NULL,
    notebook TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('know', 'fuzzy', 'unknow')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_user ON records(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_records_card ON records(card_id);
CREATE INDEX IF NOT EXISTS idx_records_notebook ON records(notebook);
