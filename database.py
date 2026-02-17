"""
SQLite database layer for IB Study Companion.

Uses raw sqlite3 with WAL mode and parameterized queries.
A schema_version table handles migrations.
"""

from __future__ import annotations

import fcntl
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g

SESSION_DIR = Path(__file__).parent / "session_data"


SCHEMA = """
-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    exam_session TEXT NOT NULL DEFAULT '',
    target_total_points INTEGER NOT NULL DEFAULT 35,
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'HL',
    target_grade INTEGER NOT NULL DEFAULT 5
);

-- Grade detail log (enriched grades with subject + command term)
CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    subject_display TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT '',
    command_term TEXT NOT NULL DEFAULT '',
    grade INTEGER NOT NULL,
    percentage INTEGER NOT NULL,
    mark_earned INTEGER NOT NULL,
    mark_total INTEGER NOT NULL,
    strengths TEXT NOT NULL DEFAULT '[]',
    improvements TEXT NOT NULL DEFAULT '[]',
    examiner_tip TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_grades_user_subject ON grades(user_id, subject_display);

-- Full grading history (from grader.py)
CREATE TABLE IF NOT EXISTS grade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    mark_earned INTEGER NOT NULL,
    mark_total INTEGER NOT NULL,
    grade INTEGER NOT NULL,
    percentage INTEGER NOT NULL,
    strengths TEXT NOT NULL DEFAULT '[]',
    improvements TEXT NOT NULL DEFAULT '[]',
    examiner_tip TEXT NOT NULL DEFAULT '',
    full_commentary TEXT NOT NULL DEFAULT '',
    model_answer TEXT NOT NULL DEFAULT '',
    raw_response TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT ''
);

-- Topic progress
CREATE TABLE IF NOT EXISTS topic_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    subtopic TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    avg_percentage REAL NOT NULL DEFAULT 0.0,
    last_practiced TEXT NOT NULL DEFAULT '',
    UNIQUE(user_id, subject, topic_id, subtopic)
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    subject TEXT NOT NULL,
    questions_attempted INTEGER NOT NULL DEFAULT 0,
    questions_answered INTEGER NOT NULL DEFAULT 0,
    avg_grade REAL NOT NULL DEFAULT 0.0,
    avg_percentage REAL NOT NULL DEFAULT 0.0,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL DEFAULT '',
    UNIQUE(user_id, date, subject)
);
CREATE INDEX IF NOT EXISTS idx_activity_user_date ON activity_log(user_id, date);

-- Spaced repetition schedule
CREATE TABLE IF NOT EXISTS review_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    command_term TEXT NOT NULL,
    last_reviewed TEXT NOT NULL DEFAULT '',
    next_review TEXT NOT NULL DEFAULT '',
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    review_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, subject, topic, command_term)
);
CREATE INDEX IF NOT EXISTS idx_review_user_next ON review_schedule(user_id, next_review);

-- Gamification
CREATE TABLE IF NOT EXISTS gamification (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_xp INTEGER NOT NULL DEFAULT 0,
    daily_xp_today INTEGER NOT NULL DEFAULT 0,
    daily_xp_date TEXT NOT NULL DEFAULT '',
    daily_goal_xp INTEGER NOT NULL DEFAULT 100,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    badges TEXT NOT NULL DEFAULT '[]',
    streak_freeze_available INTEGER NOT NULL DEFAULT 0,
    streak_freeze_used_date TEXT NOT NULL DEFAULT '',
    total_questions_answered INTEGER NOT NULL DEFAULT 0,
    total_flashcards_reviewed INTEGER NOT NULL DEFAULT 0,
    subjects_practiced TEXT NOT NULL DEFAULT '[]'
);

-- Flashcards
CREATE TABLE IF NOT EXISTS flashcards (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    next_review TEXT NOT NULL DEFAULT '',
    last_reviewed TEXT NOT NULL DEFAULT '',
    review_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_flashcards_user_review ON flashcards(user_id, next_review);

-- Misconceptions
CREATE TABLE IF NOT EXISTS misconceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL DEFAULT '',
    last_seen TEXT NOT NULL DEFAULT '',
    trending TEXT NOT NULL DEFAULT 'new',
    UNIQUE(user_id, pattern_id, subject)
);

-- Mock exam reports
CREATE TABLE IF NOT EXISTS mock_reports (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'HL',
    date TEXT NOT NULL DEFAULT '',
    total_marks_earned INTEGER NOT NULL DEFAULT 0,
    total_marks_possible INTEGER NOT NULL DEFAULT 0,
    percentage REAL NOT NULL DEFAULT 0.0,
    grade INTEGER NOT NULL DEFAULT 0,
    questions TEXT NOT NULL DEFAULT '[]',
    command_term_breakdown TEXT NOT NULL DEFAULT '{}',
    time_taken_minutes INTEGER NOT NULL DEFAULT 0,
    improvements TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT ''
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    read INTEGER NOT NULL DEFAULT 0,
    dismissed INTEGER NOT NULL DEFAULT 0,
    action_url TEXT NOT NULL DEFAULT '',
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_notif_user_dismissed ON notifications(user_id, dismissed, created_at);

-- Shared question sets
CREATE TABLE IF NOT EXISTS shared_questions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'HL',
    questions TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT '',
    import_count INTEGER NOT NULL DEFAULT 0
);

-- Study plans
CREATE TABLE IF NOT EXISTS study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generated_date TEXT NOT NULL DEFAULT '',
    exam_date TEXT NOT NULL DEFAULT '',
    daily_plans TEXT NOT NULL DEFAULT '[]'
);

-- Writing profiles
CREATE TABLE IF NOT EXISTS writing_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    verbosity TEXT NOT NULL DEFAULT '',
    terminology_usage TEXT NOT NULL DEFAULT '',
    argument_structure TEXT NOT NULL DEFAULT '',
    common_patterns TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '',
    analyzed_count INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL DEFAULT ''
);

-- Parent portal config
CREATE TABLE IF NOT EXISTS parent_config (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enabled INTEGER NOT NULL DEFAULT 0,
    token TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    student_display_name TEXT NOT NULL DEFAULT '',
    show_subject_grades INTEGER NOT NULL DEFAULT 1,
    show_recent_activity INTEGER NOT NULL DEFAULT 1,
    show_study_consistency INTEGER NOT NULL DEFAULT 1,
    show_command_term_stats INTEGER NOT NULL DEFAULT 0,
    show_insights INTEGER NOT NULL DEFAULT 1,
    show_exam_countdown INTEGER NOT NULL DEFAULT 1
);

-- Upload metadata
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    doc_type TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT '',
    chunks INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT NOT NULL DEFAULT ''
);

-- Extended Essay
CREATE TABLE IF NOT EXISTS extended_essays (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL DEFAULT '',
    research_question TEXT NOT NULL DEFAULT '',
    supervisor TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0
);

-- Internal Assessments
CREATE TABLE IF NOT EXISTS internal_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, subject)
);

-- TOK Progress
CREATE TABLE IF NOT EXISTS tok_progress (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    essay_title TEXT NOT NULL DEFAULT '',
    prescribed_title_number INTEGER NOT NULL DEFAULT 0,
    exhibition_theme TEXT NOT NULL DEFAULT ''
);

-- Milestones (shared across EE, IA, TOK)
CREATE TABLE IF NOT EXISTS milestones (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    parent_type TEXT NOT NULL DEFAULT '',
    parent_subject TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    completed INTEGER NOT NULL DEFAULT 0,
    completed_date TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, id)
);

-- CAS Reflections
CREATE TABLE IF NOT EXISTS cas_reflections (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strand TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL DEFAULT '',
    learning_outcome TEXT NOT NULL DEFAULT '',
    hours REAL NOT NULL DEFAULT 0.0
);
"""


MIGRATIONS: list[tuple[int, str]] = [
    # Version 1 = base schema, version -1 = JSON migration done.
    # -----------------------------------------------------------
    # Migration 2: Role system + school infrastructure
    (2, """
        ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student';

        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER REFERENCES schools(id) ON DELETE CASCADE,
            teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT '',
            join_code TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS class_members (
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            joined_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(class_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            config TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS assignment_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submitted_at TEXT NOT NULL DEFAULT '',
            score REAL NOT NULL DEFAULT 0,
            UNIQUE(assignment_id, user_id)
        );
    """),
    # Migration 3: Study groups + social learning
    (3, """
        CREATE TABLE IF NOT EXISTS study_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT '',
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invite_code TEXT UNIQUE NOT NULL,
            max_members INTEGER NOT NULL DEFAULT 20,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(group_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
            challenger_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            config TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS challenge_participants (
            challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            score REAL NOT NULL DEFAULT 0,
            completed_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(challenge_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS leaderboard_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL DEFAULT 'global',
            scope_id INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            xp INTEGER NOT NULL DEFAULT 0,
            rank INTEGER NOT NULL DEFAULT 0,
            period TEXT NOT NULL DEFAULT 'all',
            updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE(scope, scope_id, user_id, period)
        );
    """),
    # Migration 4: Push subscriptions
    (4, """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL DEFAULT '',
            auth TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 5: Community papers
    (5, """
        CREATE TABLE IF NOT EXISTS community_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploader_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT '',
            year INTEGER NOT NULL DEFAULT 0,
            session TEXT NOT NULL DEFAULT '',
            paper_number INTEGER NOT NULL DEFAULT 0,
            questions TEXT NOT NULL DEFAULT '[]',
            approved INTEGER NOT NULL DEFAULT 0,
            download_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS paper_ratings (
            paper_id INTEGER NOT NULL REFERENCES community_papers(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(paper_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS paper_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER NOT NULL REFERENCES community_papers(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 6: Student ability (adaptive difficulty)
    (6, """
        CREATE TABLE IF NOT EXISTS student_ability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            theta REAL NOT NULL DEFAULT 0.0,
            uncertainty REAL NOT NULL DEFAULT 1.0,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_updated TEXT NOT NULL DEFAULT '',
            UNIQUE(user_id, subject, topic)
        );
    """),
    # Migration 7: Exam sessions
    (7, """
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'HL',
            paper_number INTEGER NOT NULL DEFAULT 1,
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '',
            total_marks INTEGER NOT NULL DEFAULT 0,
            earned_marks INTEGER NOT NULL DEFAULT 0,
            grade INTEGER NOT NULL DEFAULT 0,
            questions TEXT NOT NULL DEFAULT '[]',
            answers TEXT NOT NULL DEFAULT '[]'
        );
    """),
    # Migration 8: Tutor conversations
    (8, """
        CREATE TABLE IF NOT EXISTS tutor_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            messages TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 9: User locale for i18n
    (9, """
        ALTER TABLE users ADD COLUMN locale TEXT NOT NULL DEFAULT 'en';
    """),
    # Migration 10: Agent interaction logging
    (10, """
        CREATE TABLE IF NOT EXISTS agent_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            conversation_id INTEGER,
            intent TEXT NOT NULL,
            agent TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.0,
            input_summary TEXT NOT NULL DEFAULT '',
            response_summary TEXT NOT NULL DEFAULT '',
            latency_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_agent_interactions_user
            ON agent_interactions(user_id, created_at);
    """),
    # Migration 11: Topic prerequisite edges (Knowledge Graph)
    (11, """
        CREATE TABLE IF NOT EXISTS topic_prerequisites (
            subject TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            requires_topic_id TEXT NOT NULL,
            strength REAL NOT NULL DEFAULT 1.0,
            PRIMARY KEY (subject, topic_id, requires_topic_id)
        );
    """),
    # Migration 12: Mastery states on student_ability
    (12, """
        ALTER TABLE student_ability ADD COLUMN mastery_state TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE student_ability ADD COLUMN last_correct_ratio REAL DEFAULT 0.0;
    """),
    # Migration 13: Semantic student memory
    (13, """
        CREATE TABLE IF NOT EXISTS student_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            memory_type TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE(user_id, memory_type, key)
        );
        CREATE INDEX IF NOT EXISTS idx_student_memory_user
            ON student_memory(user_id, memory_type);
    """),
    # Migration 14: Handwriting analyses (ECF Vision Agent)
    (14, """
        CREATE TABLE IF NOT EXISTS handwriting_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            question TEXT NOT NULL,
            image_hash TEXT NOT NULL,
            extracted_steps TEXT NOT NULL DEFAULT '[]',
            ecf_breakdown TEXT NOT NULL DEFAULT '{}',
            total_marks INTEGER NOT NULL DEFAULT 0,
            earned_marks INTEGER NOT NULL DEFAULT 0,
            ecf_marks INTEGER NOT NULL DEFAULT 0,
            error_line INTEGER,
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 15: Oral exam sessions
    (15, """
        CREATE TABLE IF NOT EXISTS oral_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'HL',
            text_title TEXT NOT NULL DEFAULT '',
            global_issue TEXT NOT NULL DEFAULT '',
            phase TEXT NOT NULL DEFAULT 'prepared',
            started_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '',
            transcript TEXT NOT NULL DEFAULT '[]',
            examiner_questions TEXT NOT NULL DEFAULT '[]',
            student_claims TEXT NOT NULL DEFAULT '[]',
            criterion_scores TEXT NOT NULL DEFAULT '{}',
            total_score INTEGER NOT NULL DEFAULT 0,
            feedback TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 16: Coursework IDE (sessions, drafts, data analyses)
    (16, """
        CREATE TABLE IF NOT EXISTS coursework_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doc_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            current_phase TEXT NOT NULL DEFAULT 'proposal',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS coursework_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES coursework_sessions(id) ON DELETE CASCADE,
            version INTEGER NOT NULL DEFAULT 1,
            text_content TEXT NOT NULL DEFAULT '',
            word_count INTEGER NOT NULL DEFAULT 0,
            criterion_scores TEXT NOT NULL DEFAULT '{}',
            feedback TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS data_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES coursework_sessions(id) ON DELETE CASCADE,
            raw_data TEXT NOT NULL DEFAULT '',
            analysis_result TEXT NOT NULL DEFAULT '',
            graphs TEXT NOT NULL DEFAULT '[]',
            statistical_tests TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),
    # Migration 17: Executive function (smart study plans, deadlines)
    (17, """
        CREATE TABLE IF NOT EXISTS smart_study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            generated_at TEXT NOT NULL DEFAULT '',
            days_ahead INTEGER NOT NULL DEFAULT 7,
            daily_allocations TEXT NOT NULL DEFAULT '[]',
            total_study_minutes INTEGER NOT NULL DEFAULT 0,
            priority_subjects TEXT NOT NULL DEFAULT '[]',
            burnout_risk TEXT NOT NULL DEFAULT 'low'
        );

        CREATE TABLE IF NOT EXISTS study_deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            deadline_type TEXT NOT NULL DEFAULT 'exam',
            due_date TEXT NOT NULL,
            importance TEXT NOT NULL DEFAULT 'medium',
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 18: Credit/Token Economy
    (18, """
        CREATE TABLE IF NOT EXISTS credit_balances (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            balance INTEGER NOT NULL DEFAULT 0,
            lifetime_purchased INTEGER NOT NULL DEFAULT 0,
            monthly_allocation INTEGER NOT NULL DEFAULT 0,
            last_allocation_date TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'usage',
            feature TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            balance_after INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id, created_at);
    """),

    # Migration 19: Subscription Tiers & Feature Gating
    (19, """
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            monthly_credits INTEGER NOT NULL DEFAULT 0,
            price_monthly INTEGER NOT NULL DEFAULT 0,
            price_annual INTEGER NOT NULL DEFAULT 0,
            features TEXT NOT NULL DEFAULT '[]',
            max_subjects INTEGER NOT NULL DEFAULT 3,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            plan_id TEXT NOT NULL DEFAULT 'free' REFERENCES subscription_plans(id),
            status TEXT NOT NULL DEFAULT 'active',
            started_at TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL DEFAULT '',
            cancelled_at TEXT NOT NULL DEFAULT ''
        );

        INSERT OR IGNORE INTO subscription_plans (id, name, monthly_credits, price_monthly, price_annual, features, max_subjects)
        VALUES
            ('free', 'Free', 0, 0, 0, '["text_tutoring","grading","flashcards","study_plan"]', 3),
            ('explorer', 'Explorer', 200, 999, 9990, '["text_tutoring","grading","flashcards","study_plan","oral_practice","question_gen","data_analysis","vision_agent"]', 6),
            ('scholar', 'Scholar', 500, 1999, 19990, '["text_tutoring","grading","flashcards","study_plan","oral_practice","question_gen","data_analysis","vision_agent","examiner_review","admissions","batch_grade"]', 99),
            ('diploma_pass', 'Diploma Pass', 1000, 3999, 39990, '["all"]', 99);
    """),

    # Migration 20: SOS Detection & Micro-Tutoring Pipeline
    (20, """
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            command_term TEXT NOT NULL DEFAULT '',
            failure_count INTEGER NOT NULL DEFAULT 0,
            avg_percentage REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'active',
            context_summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            resolved_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS tutoring_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            error_history TEXT NOT NULL DEFAULT '[]',
            context_summary TEXT NOT NULL DEFAULT '',
            mastery_state TEXT NOT NULL DEFAULT '',
            theta REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'pending',
            tutor_id INTEGER REFERENCES users(id),
            credits_charged INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 21: Examiner Review Pipeline
    (21, """
        CREATE TABLE IF NOT EXISTS examiner_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doc_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            submission_text TEXT NOT NULL DEFAULT '',
            ai_diagnostic TEXT NOT NULL DEFAULT '',
            ai_predicted_grade TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'submitted',
            examiner_id INTEGER REFERENCES users(id),
            examiner_feedback TEXT NOT NULL DEFAULT '',
            examiner_grade TEXT NOT NULL DEFAULT '',
            examiner_video_url TEXT NOT NULL DEFAULT '',
            credits_charged INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT NOT NULL DEFAULT '',
            assigned_at TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT '',
            delivered_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 22: Teacher Batch Grading
    (22, """
        CREATE TABLE IF NOT EXISTS batch_grading_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            assignment_title TEXT NOT NULL DEFAULT '',
            subject TEXT NOT NULL,
            doc_type TEXT NOT NULL DEFAULT 'ia',
            status TEXT NOT NULL DEFAULT 'pending',
            total_submissions INTEGER NOT NULL DEFAULT 0,
            processed_count INTEGER NOT NULL DEFAULT 0,
            results TEXT NOT NULL DEFAULT '[]',
            class_summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 23: University Admissions Profiles  (note: 24+ added in Phase 2)
    (23, """
        CREATE TABLE IF NOT EXISTS admissions_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            predicted_total INTEGER NOT NULL DEFAULT 0,
            subject_strengths TEXT NOT NULL DEFAULT '[]',
            extracurricular_summary TEXT NOT NULL DEFAULT '',
            academic_interests TEXT NOT NULL DEFAULT '',
            writing_style_summary TEXT NOT NULL DEFAULT '',
            recommended_universities TEXT NOT NULL DEFAULT '[]',
            personal_statement_draft TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE(user_id)
        );
    """),

    # Migration 24: Account lockout fields
    (24, """
        ALTER TABLE users ADD COLUMN login_attempts INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN locked_until TEXT NOT NULL DEFAULT '';
    """),

    # Migration 25: Audit log
    (25, """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at);
    """),

    # Migration 26: Password reset tokens
    (26, """
        ALTER TABLE users ADD COLUMN reset_token TEXT NOT NULL DEFAULT '';
        ALTER TABLE users ADD COLUMN reset_token_expires TEXT NOT NULL DEFAULT '';
    """),

    # Migration 27: Parent token expiration
    (27, """
        ALTER TABLE parent_config ADD COLUMN token_expires_at TEXT NOT NULL DEFAULT '';
    """),

    # Migration 28: Link users to schools
    (28, """
        ALTER TABLE users ADD COLUMN school_id INTEGER REFERENCES schools(id);
    """),

    # Migration 29: Shared flashcard decks
    (29, """
        CREATE TABLE IF NOT EXISTS shared_flashcard_decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            card_count INTEGER NOT NULL DEFAULT 0,
            cards TEXT NOT NULL DEFAULT '[]',
            download_count INTEGER NOT NULL DEFAULT 0,
            rating_sum INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 30: Study buddy preferences
    (30, """
        CREATE TABLE IF NOT EXISTS study_buddy_preferences (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            subjects TEXT NOT NULL DEFAULT '[]',
            availability TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            looking_for TEXT NOT NULL DEFAULT 'study_partner',
            updated_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 31: Admissions deadlines
    (31, """
        CREATE TABLE IF NOT EXISTS admissions_deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            university TEXT NOT NULL,
            program TEXT NOT NULL DEFAULT '',
            deadline_date TEXT NOT NULL,
            deadline_type TEXT NOT NULL DEFAULT 'application',
            status TEXT NOT NULL DEFAULT 'upcoming',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 32: AI feedback
    (32, """
        CREATE TABLE IF NOT EXISTS ai_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            interaction_id INTEGER REFERENCES agent_interactions(id),
            agent TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            context TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 33: Cost tracking columns on agent_interactions
    (33, """
        ALTER TABLE agent_interactions ADD COLUMN provider TEXT NOT NULL DEFAULT '';
        ALTER TABLE agent_interactions ADD COLUMN model TEXT NOT NULL DEFAULT '';
        ALTER TABLE agent_interactions ADD COLUMN input_tokens_est INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE agent_interactions ADD COLUMN output_tokens_est INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE agent_interactions ADD COLUMN cost_estimate_usd REAL NOT NULL DEFAULT 0.0;
        ALTER TABLE agent_interactions ADD COLUMN cache_hit INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE agent_interactions ADD COLUMN prompt_variant TEXT NOT NULL DEFAULT '';
    """),

    # Migration 34: RAG citations
    (34, """
        CREATE TABLE IF NOT EXISTS rag_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interaction_id INTEGER REFERENCES agent_interactions(id),
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chunk_source TEXT NOT NULL,
            chunk_doc_type TEXT NOT NULL,
            chunk_subject TEXT NOT NULL,
            chunk_text_hash TEXT NOT NULL,
            relevance_score REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 35: Shared summaries
    (35, """
        CREATE TABLE IF NOT EXISTS shared_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            data TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL DEFAULT ''
        );
    """),

    # Migration 36: Daily aggregates
    (36, """
        CREATE TABLE IF NOT EXISTS daily_aggregates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL DEFAULT 0.0,
            breakdown TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT '',
            UNIQUE(date, metric)
        );
    """),

    # Migration 37: Performance indexes
    (37, """
        CREATE INDEX IF NOT EXISTS idx_grades_user_timestamp ON grades(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_flashcards_user_subject ON flashcards(user_id, subject);
        CREATE INDEX IF NOT EXISTS idx_agent_interactions_created ON agent_interactions(created_at);
        CREATE INDEX IF NOT EXISTS idx_credit_tx_user_type ON credit_transactions(user_id, type);
        CREATE INDEX IF NOT EXISTS idx_community_papers_subject ON community_papers(subject, level);
    """),

    # Migration 38: Stripe payment integration columns
    (38, """
        ALTER TABLE users ADD COLUMN stripe_customer_id TEXT DEFAULT '';
        ALTER TABLE user_subscriptions ADD COLUMN stripe_subscription_id TEXT DEFAULT '';
    """),

    # Migration 39: Email verification + OAuth columns
    (39, """
        ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN email_verification_token TEXT NOT NULL DEFAULT '';
        ALTER TABLE users ADD COLUMN oauth_provider TEXT NOT NULL DEFAULT '';
        ALTER TABLE users ADD COLUMN oauth_id TEXT NOT NULL DEFAULT '';
    """),
]


def _is_postgres() -> bool:
    """Check if the configured database is PostgreSQL."""
    from pg_compat import is_postgres_url
    db_url = current_app.config.get("DATABASE", "")
    return is_postgres_url(db_url)


def get_db():
    """Return a DB connection from Flask g, creating if needed.

    Supports both SQLite (default) and PostgreSQL (when DATABASE starts
    with postgresql:// or postgres://).
    """
    if "db" not in g:
        db_url = current_app.config.get("DATABASE", str(Path(__file__).parent / "ib_study.db"))

        try:
            from pg_compat import is_postgres_url, connect_pg
            if is_postgres_url(db_url):
                g.db = connect_pg(db_url)
                return g.db
        except ImportError:
            pass

        # Default: SQLite
        g.db = sqlite3.connect(db_url)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None) -> None:
    """Teardown handler — close DB connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Execute schema DDL to create all tables."""
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def run_migrations() -> None:
    """Apply any unapplied versioned migrations.

    Uses file-based locking to prevent race conditions when multiple
    Gunicorn workers start simultaneously.
    """
    db_url = current_app.config.get("DATABASE", str(Path(__file__).parent / "ib_study.db"))
    lock_file = None

    # File-based locking only for SQLite (PostgreSQL has its own locking)
    try:
        from pg_compat import is_postgres_url
        use_pg = is_postgres_url(db_url)
    except ImportError:
        use_pg = False

    if not use_pg:
        lock_path = Path(db_url).with_suffix(".migration.lock")
        try:
            lock_file = open(lock_path, "w")
            fcntl.flock(lock_file, fcntl.LOCK_EX)
        except OSError:
            lock_file = None

    try:
        db = get_db()
        applied = {
            row["version"]
            for row in db.execute("SELECT version FROM schema_version").fetchall()
        }
        for version, sql in MIGRATIONS:
            if version not in applied:
                try:
                    db.executescript(sql)
                except (sqlite3.OperationalError, Exception) as e:
                    err_msg = str(e).lower()
                    if "duplicate column" not in err_msg and "already exists" not in err_msg:
                        raise
                db.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now().isoformat()),
                )
                db.commit()
    finally:
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()


def init_app(app) -> None:
    """Register teardown and auto-init on first request."""
    app.teardown_appcontext(close_db)

    @app.before_request
    def _ensure_db():
        if not getattr(app, "_db_initialized", False):
            init_db()
            _maybe_migrate_json()
            run_migrations()
            app._db_initialized = True


def _maybe_migrate_json() -> None:
    """Run JSON-to-SQLite migration if JSON files exist and migration not done."""
    db = get_db()
    row = db.execute(
        "SELECT version FROM schema_version WHERE version = -1"
    ).fetchone()
    if row:
        return  # Already migrated

    # Check if any JSON files exist
    json_files = list(SESSION_DIR.glob("*.json")) if SESSION_DIR.exists() else []
    if not json_files:
        # No JSON files to migrate — record schema version 1
        db.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (1, ?)",
            (datetime.now().isoformat(),),
        )
        db.commit()
        return

    migrate_json_to_sqlite()


def migrate_json_to_sqlite() -> None:
    """One-time migration from session_data/*.json to SQLite."""
    db = get_db()
    now = datetime.now().isoformat()

    # --- Create default user from profile.json ---
    profile_path = SESSION_DIR / "profile.json"
    user_id = 1
    if profile_path.exists():
        try:
            data = json.loads(profile_path.read_text())
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, exam_session, target_total_points, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (1, data.get("name", "Student"), data.get("exam_session", ""),
                 data.get("target_total_points", 35), data.get("created_at", now)),
            )
            for s in data.get("subjects", []):
                db.execute(
                    "INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (?, ?, ?, ?)",
                    (user_id, s["name"], s.get("level", "HL"), s.get("target_grade", 5)),
                )
        except (json.JSONDecodeError, KeyError):
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, created_at) VALUES (1, 'Student', ?)",
                (now,),
            )
    else:
        db.execute(
            "INSERT OR IGNORE INTO users (id, name, created_at) VALUES (1, 'Student', ?)",
            (now,),
        )

    # Ensure gamification row exists
    db.execute(
        "INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,)
    )

    # --- Grade detail log ---
    _migrate_json_file(db, SESSION_DIR / "grade_detail.json", lambda data: [
        db.execute(
            "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
            "grade, percentage, mark_earned, mark_total, strengths, improvements, examiner_tip, topic, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, e["subject"], e.get("subject_display", e["subject"]),
             e.get("level", ""), e.get("command_term", ""),
             e["grade"], e["percentage"], e["mark_earned"], e["mark_total"],
             json.dumps(e.get("strengths", [])), json.dumps(e.get("improvements", [])),
             e.get("examiner_tip", ""), e.get("topic", ""), e.get("timestamp", "")),
        ) for e in data
    ])

    # --- Grade history ---
    _migrate_json_file(db, SESSION_DIR / "grade_history.json", lambda data: [
        db.execute(
            "INSERT INTO grade_history (user_id, question, answer, mark_earned, mark_total, "
            "grade, percentage, strengths, improvements, examiner_tip, full_commentary, "
            "model_answer, raw_response, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, e["question"], e.get("answer", ""), e["mark_earned"], e["mark_total"],
             e["grade"], e["percentage"],
             json.dumps(e.get("strengths", [])), json.dumps(e.get("improvements", [])),
             e.get("examiner_tip", ""), e.get("full_commentary", ""),
             e.get("model_answer", ""), e.get("raw_response", ""), e.get("timestamp", "")),
        ) for e in data
    ])

    # --- Topic progress ---
    tp_path = SESSION_DIR / "topic_progress.json"
    if tp_path.exists():
        try:
            data = json.loads(tp_path.read_text())
            for subject, topics_dict in data.items():
                for topic_id, attempts in topics_dict.items():
                    for a in attempts:
                        db.execute(
                            "INSERT OR IGNORE INTO topic_progress "
                            "(user_id, subject, topic_id, subtopic, attempts, avg_percentage, last_practiced) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (user_id, subject, topic_id, a["subtopic"],
                             a.get("attempts", 0), a.get("avg_percentage", 0),
                             a.get("last_practiced", "")),
                        )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Activity log ---
    _migrate_json_file(db, SESSION_DIR / "activity_log.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO activity_log "
            "(user_id, date, subject, questions_attempted, questions_answered, "
            "avg_grade, avg_percentage, duration_minutes, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, e["date"], e["subject"],
             e.get("questions_attempted", 0), e.get("questions_answered", 0),
             e.get("avg_grade", 0), e.get("avg_percentage", 0),
             e.get("duration_minutes", 0), e.get("timestamp", "")),
        ) for e in data
    ])

    # --- Review schedule ---
    _migrate_json_file(db, SESSION_DIR / "review_schedule.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO review_schedule "
            "(user_id, subject, topic, command_term, last_reviewed, next_review, "
            "interval_days, ease_factor, review_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, e["subject"], e["topic"], e["command_term"],
             e.get("last_reviewed", ""), e.get("next_review", ""),
             e.get("interval_days", 1), e.get("ease_factor", 2.5),
             e.get("review_count", 0)),
        ) for e in data
    ])

    # --- Gamification ---
    gam_path = SESSION_DIR / "gamification.json"
    if gam_path.exists():
        try:
            g_data = json.loads(gam_path.read_text())
            db.execute(
                "UPDATE gamification SET total_xp=?, daily_xp_today=?, daily_xp_date=?, "
                "daily_goal_xp=?, current_streak=?, longest_streak=?, badges=?, "
                "streak_freeze_available=?, streak_freeze_used_date=?, "
                "total_questions_answered=?, total_flashcards_reviewed=?, subjects_practiced=? "
                "WHERE user_id=?",
                (g_data.get("total_xp", 0), g_data.get("daily_xp_today", 0),
                 g_data.get("daily_xp_date", ""), g_data.get("daily_goal_xp", 100),
                 g_data.get("current_streak", 0), g_data.get("longest_streak", 0),
                 json.dumps(g_data.get("badges", [])),
                 g_data.get("streak_freeze_available", 0), g_data.get("streak_freeze_used_date", ""),
                 g_data.get("total_questions_answered", 0), g_data.get("total_flashcards_reviewed", 0),
                 json.dumps(g_data.get("subjects_practiced", [])), user_id),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Flashcards ---
    _migrate_json_file(db, SESSION_DIR / "flashcards.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO flashcards "
            "(id, user_id, front, back, subject, topic, source, interval_days, "
            "ease_factor, next_review, last_reviewed, review_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (c["id"], user_id, c["front"], c["back"], c["subject"],
             c.get("topic", ""), c.get("source", ""), c.get("interval_days", 1),
             c.get("ease_factor", 2.5), c.get("next_review", ""),
             c.get("last_reviewed", ""), c.get("review_count", 0),
             c.get("created_at", "")),
        ) for c in data
    ])

    # --- Misconceptions ---
    _migrate_json_file(db, SESSION_DIR / "misconceptions.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO misconceptions "
            "(user_id, pattern_id, subject, count, first_seen, last_seen, trending) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, e["pattern_id"], e["subject"], e.get("count", 1),
             e.get("first_seen", ""), e.get("last_seen", ""), e.get("trending", "new")),
        ) for e in data
    ])

    # --- Mock reports ---
    _migrate_json_file(db, SESSION_DIR / "mock_reports.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO mock_reports "
            "(id, user_id, subject, level, date, total_marks_earned, total_marks_possible, "
            "percentage, grade, questions, command_term_breakdown, time_taken_minutes, "
            "improvements, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (r["id"], user_id, r["subject"], r.get("level", "HL"), r.get("date", ""),
             r.get("total_marks_earned", 0), r.get("total_marks_possible", 0),
             r.get("percentage", 0), r.get("grade", 0),
             json.dumps(r.get("questions", [])),
             json.dumps(r.get("command_term_breakdown", {})),
             r.get("time_taken_minutes", 0),
             json.dumps(r.get("improvements", [])), r.get("created_at", "")),
        ) for r in data
    ])

    # --- Notifications ---
    _migrate_json_file(db, SESSION_DIR / "notifications.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO notifications "
            "(id, user_id, type, title, body, created_at, read, dismissed, action_url, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (n["id"], user_id, n["type"], n["title"], n.get("body", ""),
             n.get("created_at", ""), 1 if n.get("read") else 0,
             1 if n.get("dismissed") else 0,
             n.get("action_url", ""), json.dumps(n.get("data", {}))),
        ) for n in data
    ])

    # --- Shared questions ---
    _migrate_json_file(db, SESSION_DIR / "shared_questions.json", lambda data: [
        db.execute(
            "INSERT OR IGNORE INTO shared_questions "
            "(id, user_id, title, description, author, subject, topic, level, "
            "questions, created_at, import_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (qs["id"], user_id, qs["title"], qs.get("description", ""),
             qs.get("author", ""), qs["subject"], qs.get("topic", ""),
             qs.get("level", "HL"), json.dumps(qs.get("questions", [])),
             qs.get("created_at", ""), qs.get("import_count", 0)),
        ) for qs in data
    ])

    # --- Study plan ---
    sp_path = SESSION_DIR / "study_plan.json"
    if sp_path.exists():
        try:
            sp_data = json.loads(sp_path.read_text())
            db.execute(
                "INSERT INTO study_plans (user_id, generated_date, exam_date, daily_plans) "
                "VALUES (?, ?, ?, ?)",
                (user_id, sp_data.get("generated_date", ""),
                 sp_data.get("exam_date", ""),
                 json.dumps(sp_data.get("daily_plans", []))),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Writing profile ---
    wp_path = SESSION_DIR / "writing_profile.json"
    if wp_path.exists():
        try:
            wp = json.loads(wp_path.read_text())
            db.execute(
                "INSERT OR IGNORE INTO writing_profiles "
                "(user_id, verbosity, terminology_usage, argument_structure, "
                "common_patterns, summary, analyzed_count, last_updated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, wp.get("verbosity", ""), wp.get("terminology_usage", ""),
                 wp.get("argument_structure", ""),
                 json.dumps(wp.get("common_patterns", [])),
                 wp.get("summary", ""), wp.get("analyzed_count", 0),
                 wp.get("last_updated", "")),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Parent config ---
    pc_path = SESSION_DIR / "parent_config.json"
    if pc_path.exists():
        try:
            pc = json.loads(pc_path.read_text())
            db.execute(
                "INSERT OR IGNORE INTO parent_config "
                "(user_id, enabled, token, created_at, student_display_name, "
                "show_subject_grades, show_recent_activity, show_study_consistency, "
                "show_command_term_stats, show_insights, show_exam_countdown) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, 1 if pc.get("enabled") else 0,
                 pc.get("token", ""), pc.get("created_at", ""),
                 pc.get("student_display_name", ""),
                 1 if pc.get("show_subject_grades", True) else 0,
                 1 if pc.get("show_recent_activity", True) else 0,
                 1 if pc.get("show_study_consistency", True) else 0,
                 1 if pc.get("show_command_term_stats", False) else 0,
                 1 if pc.get("show_insights", True) else 0,
                 1 if pc.get("show_exam_countdown", True) else 0),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Uploads ---
    uploads_path = SESSION_DIR / "uploads.json"
    if uploads_path.exists():
        try:
            uploads_data = json.loads(uploads_path.read_text())
            for u in uploads_data:
                db.execute(
                    "INSERT OR IGNORE INTO uploads "
                    "(id, user_id, filename, doc_type, subject, level, chunks, uploaded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (u["id"], user_id, u["filename"], u.get("doc_type", ""),
                     u.get("subject", ""), u.get("level", ""),
                     u.get("chunks", 0), u.get("uploaded_at", "")),
                )
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Lifecycle ---
    lc_path = SESSION_DIR / "lifecycle.json"
    if lc_path.exists():
        try:
            lc = json.loads(lc_path.read_text())

            # Extended Essay
            ee = lc.get("extended_essay", {})
            db.execute(
                "INSERT OR IGNORE INTO extended_essays (user_id, subject, research_question, supervisor, word_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, ee.get("subject", ""), ee.get("research_question", ""),
                 ee.get("supervisor", ""), ee.get("word_count", 0)),
            )
            sort_order = 0
            for m in ee.get("milestones", []):
                db.execute(
                    "INSERT OR IGNORE INTO milestones "
                    "(user_id, id, parent_type, parent_subject, title, due_date, completed, completed_date, notes, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, m["id"], "ee", "", m.get("title", ""),
                     m.get("due_date", ""), 1 if m.get("completed") else 0,
                     m.get("completed_date", ""), m.get("notes", ""), sort_order),
                )
                sort_order += 1

            # Internal Assessments
            for ia in lc.get("internal_assessments", []):
                db.execute(
                    "INSERT OR IGNORE INTO internal_assessments (user_id, subject, title, word_count) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, ia.get("subject", ""), ia.get("title", ""), ia.get("word_count", 0)),
                )
                sort_order = 0
                for m in ia.get("milestones", []):
                    db.execute(
                        "INSERT OR IGNORE INTO milestones "
                        "(user_id, id, parent_type, parent_subject, title, due_date, completed, completed_date, notes, sort_order) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (user_id, m["id"], "ia", ia.get("subject", ""),
                         m.get("title", ""), m.get("due_date", ""),
                         1 if m.get("completed") else 0,
                         m.get("completed_date", ""), m.get("notes", ""), sort_order),
                    )
                    sort_order += 1

            # TOK
            tok = lc.get("tok", {})
            db.execute(
                "INSERT OR IGNORE INTO tok_progress "
                "(user_id, essay_title, prescribed_title_number, exhibition_theme) "
                "VALUES (?, ?, ?, ?)",
                (user_id, tok.get("essay_title", ""),
                 tok.get("prescribed_title_number", 0),
                 tok.get("exhibition_theme", "")),
            )
            sort_order = 0
            for m in tok.get("milestones", []):
                db.execute(
                    "INSERT OR IGNORE INTO milestones "
                    "(user_id, id, parent_type, parent_subject, title, due_date, completed, completed_date, notes, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, m["id"], "tok", "", m.get("title", ""),
                     m.get("due_date", ""), 1 if m.get("completed") else 0,
                     m.get("completed_date", ""), m.get("notes", ""), sort_order),
                )
                sort_order += 1

            # CAS reflections
            for r in lc.get("cas_reflections", []):
                db.execute(
                    "INSERT OR IGNORE INTO cas_reflections "
                    "(id, user_id, strand, title, description, date, learning_outcome, hours) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (r.get("id", ""), user_id, r.get("strand", ""),
                     r.get("title", ""), r.get("description", ""),
                     r.get("date", ""), r.get("learning_outcome", ""),
                     r.get("hours", 0)),
                )
        except (json.JSONDecodeError, KeyError):
            pass

    db.commit()

    # Record migration done
    db.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (-1, ?)",
        (now,),
    )
    db.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (1, ?)",
        (now,),
    )
    db.commit()

    # Rename JSON files as safety net
    for f in SESSION_DIR.glob("*.json"):
        try:
            f.rename(f.with_suffix(".json.migrated"))
        except OSError:
            pass


def _migrate_json_file(db, path: Path, inserter) -> None:
    """Helper: load a JSON list file and run the inserter lambda."""
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            inserter(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
