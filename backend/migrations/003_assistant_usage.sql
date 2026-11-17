-- AI 건강 비서 하루 질문 수(2026-11-17). 질문 원문·답변은 저장하지 않고 횟수만 센다.
-- 회원 탈퇴 시 함께 지워진다(ON DELETE CASCADE).
CREATE TABLE IF NOT EXISTS assistant_usage (
 user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 day date NOT NULL,
 questions integer NOT NULL CHECK (questions >= 0),
 fallbacks integer NOT NULL DEFAULT 0 CHECK (fallbacks >= 0),
 PRIMARY KEY (user_id, day)
);
CREATE INDEX IF NOT EXISTS assistant_usage_day ON assistant_usage(day);
INSERT INTO schema_migrations(version) VALUES (3) ON CONFLICT DO NOTHING;
