# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary user: a single IB DP Computer Science teacher (the product's owner and sole admin), managing one class of students directly. Secondary users: their enrolled students (HL/SL levels within the same class), who take assigned tests/quizzes, read assigned content, and study flashcards.

## Product Purpose

Gives the teacher one connected place to author, assign, and mark curriculum-exact assessment and study material — timed tests, quizzes, flashcards, reading — for their own IB DP CS class, with AI assistance for grading written answers and generating per-student feedback. Replaces a patchwork of generic tools (e.g. Google Classroom + a generic quiz app) with something built directly around this teacher's own syllabus and question bank.

## Positioning

Neither "exact-to-syllabus content" nor "AI-assisted marking" alone is the differentiator — it's having both together in one system: every question, reading page, and flashcard maps to the real IB DP CS syllabus and the teacher's own authored materials (not generic templates), and written answers get AI-assisted, confidence-tiered marking with teacher review/override, rather than requiring the teacher to grade everything by hand or use an ungraded generic quiz tool.

## Operating Context

- Single school, single teacher (the owner/admin), one class roster with HL/SL sub-levels.
- Teacher authors content (test papers via Test Builder, quizzes, unit plans, flashcards) and assigns it to the whole class, a level (HL/SL), or individual students.
- Students log in (no public registration — accounts are provisioned by the teacher), complete assigned work — timed single-attempt tests entered via a join code, quizzes, reading, flashcards — and receive AI-assisted or teacher-reviewed feedback and reports.
- No mobile app; used in-browser on desktop and occasionally tablet/mobile.

## Capabilities and Constraints

- Flask + Jinja, server-rendered (no JS framework build step, no hot-module-reload dev server); SQLAlchemy models; Flask-Migrate for schema changes.
- Real content sources treated as ground truth, never fabricated: a hand-authored question bank (`questions.xlsx`, ~1,680 questions across the Theme A/B syllabus) and existing "Book_93" reading content on the same syllabus.
- Privacy constraint (owner's explicit note): avoid displaying or storing personal identifiers beyond what's operationally necessary for teaching/grading. This isn't a formal accessibility requirement, so it's recorded here rather than under Accessibility & Inclusion.
- Permanently single-tenant by design (see Product Principles) — no multi-teacher, multi-class-owner, or multi-school architecture is needed.

## Evidence on Hand

- Real question bank: `questions.xlsx` (~1,680 questions, Theme A/B, IB DP Computer Science syllabus).
- Existing "Book_93" reading/syllabus content already imported and in use elsewhere in the app.
- No marketing copy, testimonials, or public-facing content exists or is needed — this is an internal single-classroom tool, not a public product.

## Product Principles

1. Curriculum truth over genericism — content maps to the real syllabus and the teacher's own materials; never invent question content, marks schemes, or reading material.
2. AI assists grading and feedback; the teacher remains final authority (confidence-tiered review queues, manual override on any AI-assigned mark).
3. Design for one real owner's daily workflow, not generic multi-tenant SaaS patterns — no admin-of-admins, billing, or tenant-onboarding flows.
4. Minimize personal-identifier exposure — don't display or store student PII beyond what the teaching/grading function actually requires.
5. Extend the existing Flask/Jinja architecture rather than migrating stacks.

## Accessibility & Inclusion

No formal accessibility standard (e.g. WCAG level) has been established. See the personal-identifier constraint under Capabilities and Constraints.
