-- RAG knowledge base schema. Kept deliberately small: exact tag filtering
-- happens in SQL; fuzzy similarity happens via a (not-yet-built) embeddings
-- table/file. This schema is topic-agnostic — distinct topics/papers are
-- NOT partitioned in here (a question can carry multiple topic tags, so
-- content can't live inside a single topic's file). Partitioning happens
-- at the JSON source-file level instead: question CONTENT lives one file
-- per paper (data/processed/questions/<paper>_<sitting>.json), and TAG
-- ASSIGNMENTS live one file per topic/technique (data/processed/topics/ and
-- data/processed/techniques/, each just a list of question_ids). See
-- scripts/build_db.py.

-- ============================================================
-- Questions: one row per past-paper question, across all topics
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,          -- e.g. "P1_June2022_Q15"
    spec TEXT NOT NULL,           -- e.g. "9MA0"
    paper TEXT NOT NULL,          -- e.g. "P1"
    sitting TEXT NOT NULL,        -- e.g. "June2022"
    q_num TEXT NOT NULL,          -- e.g. "15"
    total_marks INTEGER,
    question_text TEXT NOT NULL,
    mark_scheme_text TEXT NOT NULL,
    source_qp_file TEXT,          -- provenance: raw QP .txt this was transcribed from
    source_ms_file TEXT,          -- provenance: raw MS .txt this was transcribed from
    low_confidence INTEGER NOT NULL DEFAULT 0,  -- 1 if transcription/tagging needs a human check
    notes TEXT DEFAULT ''          -- explains what's uncertain when low_confidence=1
);

-- ============================================================
-- Question <-> tag links (many-to-many). tag_value must match
-- an id declared in tags.json — enforced at build time, not here.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_tags (
    question_id TEXT NOT NULL REFERENCES questions(id),
    tag_type TEXT NOT NULL CHECK (tag_type IN ('topic', 'technique')),
    tag_value TEXT NOT NULL,      -- must match an id in tags.json
    PRIMARY KEY (question_id, tag_type, tag_value)
);

-- ============================================================
-- Techniques: your worked explanation of a method/skill, shared
-- across whichever topics use it (see tags.json topics[] on each)
-- ============================================================
CREATE TABLE IF NOT EXISTS techniques (
    id TEXT PRIMARY KEY,          -- matches an id in tags.json
    title TEXT NOT NULL,
    content TEXT NOT NULL,        -- the worked explanation of the technique
    contrast_with TEXT            -- comma-separated technique ids this is often confused with
);

-- ============================================================
-- Examiner notes: real examiner-report commentary only — never
-- fabricated. Empty until real ER data is scraped and added.
-- ============================================================
CREATE TABLE IF NOT EXISTS examiner_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT REFERENCES questions(id),  -- NULL if a general note, not tied to one question
    tag_value TEXT,                              -- technique/topic this note is about
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_question_tags_value ON question_tags(tag_value);
