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
    id TEXT PRIMARY KEY,          -- e.g. "P1_June2022_Q15", "P3_June2019_stats_Q2", "IAL2018_WST01_Jan2020_Q3"
    spec TEXT NOT NULL,           -- e.g. "9MA0" (same as qualification)
    paper TEXT NOT NULL,          -- e.g. "P1", "P3", or a legacy unit code "WST01"
    sitting TEXT NOT NULL,        -- e.g. "June2022", "Jan2020"
    paper_id TEXT NOT NULL,       -- e.g. "P1_June2022", "P3_June2019_stats"; joins sources.paper_id
    qualification TEXT NOT NULL,  -- "9MA0" | "IAL-2018" | "IAL-2013" | "GCE-2008"
    unit TEXT,                    -- e.g. "9MA0-01", "9MA0-31", "WST01", "6683"
    component TEXT NOT NULL,      -- "pure" | "stats" | "mech"
    status TEXT NOT NULL CHECK (status IN ('current', 'legacy')),  -- current = 9MA0 paper
    uses_large_data_set INTEGER NOT NULL DEFAULT 0,  -- 9MA0 statistics questions about the LDS
    q_num TEXT NOT NULL,          -- e.g. "15"
    total_marks INTEGER,
    question_text TEXT NOT NULL,
    mark_scheme_text TEXT NOT NULL,
    source_qp_file TEXT,          -- provenance: raw QP .txt this was transcribed from
    source_ms_file TEXT,          -- provenance: raw MS .txt this was transcribed from
    low_confidence INTEGER NOT NULL DEFAULT 0,  -- 1 if transcription/tagging needs a human check
    notes TEXT DEFAULT '',         -- explains what's uncertain when low_confidence=1
    stem TEXT,                    -- shared preamble before the first part (see question_parts)
    qp_first_page INTEGER,        -- question paper PDF pages holding the question (scripts/find_figures.py);
    qp_last_page INTEGER,         --   link as <sources.qp_url>#page=<qp_first_page>
    has_figure INTEGER NOT NULL DEFAULT 0,
    figure_pages TEXT             -- JSON list of PDF pages with the question's figures, e.g. "[22]"
);

-- ============================================================
-- Question parts: the smallest units carrying their own marks on the
-- question paper, e.g. "a", "b(i)". Single-part questions have one row
-- with label NULL. Built by scripts/split_parts.py.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_parts (
    question_id TEXT NOT NULL REFERENCES questions(id),
    part_index INTEGER NOT NULL,  -- 0-based order on the paper
    label TEXT,                   -- "a", "b(i)", "ii"; NULL for a single-part question
    marks INTEGER NOT NULL,
    text TEXT NOT NULL,
    mark_scheme TEXT NOT NULL,
    spec_refs TEXT,               -- JSON list of 9MA0 content refs (data/processed/spec_9ma0.json), e.g. '["S4.1"]'
    PRIMARY KEY (question_id, part_index)
);

-- ============================================================
-- Question <-> tag links (many-to-many). tag_value must match
-- an id declared in tags.json — enforced at build time, not here.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_tags (
    question_id TEXT NOT NULL REFERENCES questions(id),
    part_label TEXT,              -- NULL = whole question (topics, question types); "a", "b(i)" for skills
    tag_type TEXT NOT NULL CHECK (tag_type IN ('topic', 'technique', 'question_type', 'skill')),
    tag_value TEXT NOT NULL       -- must match an id in tags.json
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_question_tags_unique
    ON question_tags(question_id, COALESCE(part_label, ''), tag_type, tag_value);

-- ============================================================
-- Two-layer tag vocabulary (Phase 2f). Question types are the NARROW
-- "same kind of question" layer (one per question); skills are the BROAD
-- layer (several per part), each in a parent group for fallback.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_types (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    topic TEXT,                   -- the main topic id
    definition TEXT
);
CREATE TABLE IF NOT EXISTS skill_groups (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    group_id TEXT NOT NULL REFERENCES skill_groups(id),
    description TEXT,
    formula_booklet INTEGER NOT NULL DEFAULT 0  -- 1 if the key formula is printed in the 9MA0 booklet
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
-- Examiner notes: verbatim quotes from Pearson's Principal Examiner
-- Feedback reports only — never fabricated. build_db.py rejects any quote
-- that doesn't appear in its source report text (data/raw/examiner-reports/).
-- ============================================================
CREATE TABLE IF NOT EXISTS examiner_notes (
    id TEXT PRIMARY KEY,          -- e.g. "P1_June2022_Q15_n3"; "P1_June2022_G_n1" for paper-level notes
    question_id TEXT REFERENCES questions(id),  -- NULL for a paper-level (general) note
    part_label TEXT,              -- e.g. "a", "b(i)"; NULL if about the whole question
    kind TEXT NOT NULL CHECK (kind IN ('did_well', 'pitfall', 'general')),
    quote TEXT NOT NULL,          -- verbatim text from the report
    display TEXT,                 -- optional: same text with garbled maths symbols repaired (human-review item)
    source_file TEXT NOT NULL,    -- e.g. "examiner-reports/P1_June2022_ER.txt"
    page INTEGER                  -- computed at build time from the report's page breaks
);

-- ============================================================
-- Question performance: how the cohort did, per question/part, as stated
-- in the examiner report. rating is backed by an examiner_notes quote.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_performance (
    question_id TEXT NOT NULL REFERENCES questions(id),
    part_label TEXT,              -- NULL = whole question
    mean_mark REAL,               -- only where the report states it
    max_mark INTEGER,
    full_marks_pct REAL,          -- % of candidates scoring full marks, only where the report states it
    full_marks_pct_note_id TEXT REFERENCES examiner_notes(id),  -- note quoting that figure
    rating TEXT CHECK (rating IN ('well_answered', 'mixed', 'poorly_answered')),
    evidence_note_id TEXT REFERENCES examiner_notes(id),
    PRIMARY KEY (question_id, part_label)
);

-- ============================================================
-- Sources: links to the original paper, mark scheme and examiner report for
-- every paper, so answers can cite them. Generated by
-- scripts/build_sources.py into sources.json; loaded by build_db.py.
-- ============================================================
CREATE TABLE IF NOT EXISTS sources (
    paper_id TEXT PRIMARY KEY,    -- e.g. "P1_June2022", "P3_June2019_mech", "IAL2018_WST01_Jan2020"; joins questions.paper_id
    spec TEXT NOT NULL,           -- "9MA0", "8MA0", "IAL-2018", "IAL-2013", "GCE-2008"
    paper TEXT NOT NULL,          -- "P1".."P3", "ASP1", "ASP2"
    sitting TEXT NOT NULL,        -- "June2022", "Oct2020", "Nov2021", "Specimen", "Sample"
    component TEXT,               -- "mech" / "stats" for split Paper 3 / AS Paper 2, else NULL
    official INTEGER NOT NULL,    -- 0 for Pearson's "Sample" papers
    in_knowledge_base INTEGER NOT NULL,
    qp_url TEXT, qp_viewer_url TEXT,
    ms_url TEXT, ms_viewer_url TEXT,
    er_url TEXT,                  -- Pearson examiner report
    pmt_model_answers_url TEXT    -- unofficial, PMT-written
);

CREATE INDEX IF NOT EXISTS idx_question_tags_value ON question_tags(tag_value);
