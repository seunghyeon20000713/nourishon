-- 소스 마이그레이션입니다. 사용자 데이터나 비밀값을 포함하지 않습니다.
CREATE TABLE IF NOT EXISTS schema_migrations (
 version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS users (
 id uuid PRIMARY KEY, username text NOT NULL UNIQUE,
 password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 csrf_token text NOT NULL, expires_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS profiles (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 nickname text NOT NULL CHECK(length(nickname) BETWEEN 1 AND 20),
 revision integer NOT NULL DEFAULT 0,
 settings jsonb, estimate jsonb, exercise_input jsonb, exercise_plan jsonb,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS profiles_user ON profiles(user_id);
CREATE TABLE IF NOT EXISTS body_measurements (
 id uuid NOT NULL, profile_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 measured_on date NOT NULL, weight_kg numeric NOT NULL CHECK(weight_kg > 0),
 composition jsonb NOT NULL, position integer NOT NULL,
 PRIMARY KEY(profile_id,id)
);
CREATE TABLE IF NOT EXISTS meals (
 id uuid NOT NULL, profile_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
 eaten_on date NOT NULL, kind text NOT NULL CHECK(kind IN ('아침','점심','저녁','간식')),
 calculation jsonb NOT NULL, position integer NOT NULL,
 PRIMARY KEY(profile_id,id)
);
CREATE TABLE IF NOT EXISTS auth_attempts (
 bucket text PRIMARY KEY, attempts integer NOT NULL, window_end timestamptz NOT NULL
);
INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
