-- 개인 운동 기록의 계산 스냅샷. 기존 데이터는 보존한다.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS activity_records jsonb NOT NULL DEFAULT '[]'::jsonb;
INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT DO NOTHING;
