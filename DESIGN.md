---
name: The Oracle
description: A clean, modern learning environment for IB DP Computer Science — reading, revising, and assessment, not another AI-slop dashboard or flashcard mill.
colors:
  study-violet: "#8366e8"
  study-violet-light: "#9d84ff"
  study-violet-dark: "#6b52cc"
  progress-emerald: "#10b981"
  caution-amber: "#f59e0b"
  alert-red: "#ef4444"
  signal-blue: "#3b82f6"
  paper-white: "#ffffff"
  paper-grey: "#f8f9fa"
  ink-dark: "#1a1a1a"
  ink-muted: "#6b7280"
  hairline: "#e5e7eb"
  tint: "color-mix(in srgb, #8366e8 12%, transparent)"
  surface-hover: "#f0f4f8"
typography:
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontWeight: 700
    fontSize: "1.45rem"
    lineHeight: 1.25
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontWeight: 600
    fontSize: "1rem"
    lineHeight: 1.35
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontWeight: 400
    fontSize: "0.875rem"
    lineHeight: 1.5
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontWeight: 600
    fontSize: "0.75rem"
    letterSpacing: "0.04em"
  reading:
    fontFamily: "'Libertinus Serif', ui-serif, Georgia, 'Times New Roman', serif"
    fontWeight: 400
    lineHeight: 1.6
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
    fontWeight: 400
rounded:
  control: "6px"
  sm: "8px"
  md: "12px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.study-violet}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.control}"
    padding: "0.55rem 1.1rem"
  button-primary-hover:
    backgroundColor: "{colors.study-violet-dark}"
  button-danger:
    backgroundColor: "{colors.alert-red}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.control}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dark}"
    rounded: "{rounded.control}"
    padding: "0.54rem 1.1rem"
  button-ghost-hover:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.study-violet}"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dark}"
    rounded: "{rounded.control}"
    padding: "0.4rem 0.7rem"
  button-text-hover:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.study-violet}"
  card:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink-dark}"
    rounded: "{rounded.md}"
    padding: "1.25rem"
  input:
    backgroundColor: "{colors.paper-grey}"
    textColor: "{colors.ink-dark}"
    rounded: "{rounded.control}"
    padding: "0.5rem 0.7rem"
---

# Design System: The Oracle

## Overview

**Creative North Star: "The Reading Room, Rebuilt"**

A classic academic reading room — quiet, considered, built for actual study — remade with a contemporary web surface instead of dated edtech chrome. The product spans two very different jobs (a teacher authoring and marking on one side, students reading/revising/testing on the other), but both sides share the same visual language: one deliberate violet accent against calm neutral paper tones, Inter's clean geometric-humanist forms, and soft ambient depth rather than flashy motion or decoration. The explicit anti-references are (a) generic "AI-generated dashboard" tells — gradient hero blocks, colored border-left accent bars, emoji standing in for an icon system, pale washed-out secondary buttons — and (b) generic edtech blandness — a bare Quizlet/Wikipedia look with no point of view. Gen Z students using the student-facing side should read it as genuinely current, not as either of those defaults.

**Key Characteristics:**
- One accent color (violet), used deliberately rather than scattered across every element.
- Calm, mostly-flat surfaces; depth is ambient (a constant soft lift), never a hover trick.
- A strict three-tier action hierarchy (filled primary / outlined ghost / plain text) so importance is always legible at a glance.
- Icons are drawn (consistent-stroke SVG), never emoji or unicode glyphs standing in for an icon system.
- Two typefaces, split by job, not by decoration: Inter for every operating surface, Libertinus Serif for the reading surface alone.
- Structure is static, controls respond — depth describes what a thing *is*, never whether it can be clicked.

## Colors

One violet accent carries intent; everything else is quiet paper and ink, plus a small semantic set for state.

### Primary
- **Study Violet** (`#8366e8`, dark theme `#9d84ff`): the one accent — primary buttons, active tab/pill states, focus rings, selected-row highlights. Used sparingly by convention (one filled primary action per screen), not as a general decoration.

### Neutral
- **Paper White** (`#ffffff`, dark theme `#17181f`): card and page background.
- **Paper Grey** (`#f8f9fa`, dark theme `#0f1014`): sunken/secondary surface (page background behind cards, subtle section fills).
- **Ink Dark** (`#1a1a1a`, dark theme `#ececf1`): primary text.
- **Ink Muted** (`#6b7280`, dark theme `#9a9aa8`): secondary/meta text (timestamps, counts, helper copy) — reserved for text that is genuinely secondary, not for buttons that still need to read as clickable.
- **Hairline** (`#e5e7eb`, dark theme `#262833`): borders and dividers.

### Semantic (state, not decoration)
- **Progress Emerald** (`#10b981`, ink `#047857`): success states, "published"/"completed"-type signals.
- **Caution Amber** (`#f59e0b`, ink `#b45309`): warnings (e.g. HL-only content flags).
- **Alert Red** (`#ef4444`, ink `#b91c1c`): destructive actions and errors.
- **Signal Blue** (`#3b82f6`): informational accents, distinct from the primary violet.

### Named Rules
**The One Accent Rule.** Study Violet is the only color used to mean "this is the primary action here." Semantic colors (emerald/amber/red/blue) mean state, never emphasis — don't reach for green or blue to make something feel important.

**The Fill-Versus-Ink Rule.** Every semantic hue has two jobs and two values. The saturated value (`#10b981`, `#f59e0b`, `#ef4444`) is for **fills, borders, dots, and large numerals**. Small text takes the **ink** step (`#047857`, `#b45309`, `#b91c1c`), because on a white ground the saturated values measure 2.5:1, 2.2:1 and 3.8:1 — all below the 4.5:1 floor for body-sized text. A green "saved" hint or an amber warning line set in the fill value is unreadable in bright light, which on a timed exam screen is a real failure and not a nitpick. On dark grounds the bright values already clear the threshold, so fill and ink converge.

## Typography

**Interface Font:** Inter (with a full native system-font fallback stack) — imported once in `style.css`.
**Reading Font:** Libertinus Serif (falling back to Georgia / Times New Roman) — scoped to the reading experience only.
**Mono:** the native `ui-monospace` stack (`--dp-mono`), for code, data, and measured values inside dynamic page modules.

**Character:** One interface voice, one reading voice. Inter carries every screen where the user is *operating* the product — authoring, marking, navigating, testing. Libertinus Serif carries the one screen where the user is *reading*, and only there: a book-weight academic serif chosen to make long-form syllabus content feel like a book rather than a web page, closer to a Kindle than to a docs site. That split is the whole type system; there is no third voice.

Display and body separate by **weight and size, not by family**. A surface that wants a more emphatic heading reaches for Inter 700 at a larger size, never for a different typeface.

### Hierarchy
- **Headline** (700, ~1.4–1.5rem): page titles (`h1` in card headers).
- **Title** (600, ~0.9–1.1rem): section headings, card titles.
- **Body** (400, ~0.85–0.9rem): running text, table cells, form labels.
- **Label** (600–700, ~0.7–0.8rem, uppercase + letter-spacing on pills): status pills, category tags, small meta labels.
- **Reading** (Libertinus Serif 400/700, generous line-height): expanded page titles and long-form body on the reading surface. Libertinus ships 400 and 700 only — never specify 500 or 600 against it, or the browser will synthesise a weight.

### Named Rules
**The Two Voices Rule.** Inter for operating, Libertinus Serif for reading. A surface gets the serif only if the user's job there is sustained reading — not because a heading wants to feel special. Any third family arriving on a single screen is drift, not art direction: the app previously carried Space Grotesk on the test paper and Plus Jakarta Sans on the EE exemplars library, and both were consolidated back to Inter for exactly this reason.

## Layout

Card-based composition: a page is a stack of bordered, softly-shadowed panels (`.admin-card` / `.tb-card`) inside a max-width container, not a full-bleed dashboard grid. Related controls group tightly (`gap: 0.4–0.6rem`); distinct groups of controls separate with a deliberately larger gap (`gap: 1.5rem`) rather than every element sharing one spacing value — see the Test Builder's action row for the current reference implementation of that rhythm. Responsive behavior is structural, not just reflow: multi-column edit layouts collapse to one column under ~900px, and button groups wrap with the trailing (destructive) group staying right-aligned via `margin-left: auto` rather than sliding to wherever it lands.

**Motion** is short and eased, never bouncy: state changes run at 150ms, and anything with authored character uses the `--ease-out` token (`cubic-bezier(0.23, 1, 0.32, 1)`) — a sharp exponential ease-out from an already-visible default, so nothing appears to pop into existence. `--ease-in-out` (`cubic-bezier(0.77, 0, 0.175, 1)`) is reserved for reversible transitions that need to feel symmetrical (drawers, sidebar collapse). Dynamic page modules carry their own `--dp-ease` (`cubic-bezier(.16, 1, .3, 1)`) for interactive demonstrations. Page-level entrances are limited to one 150ms fade on the main content region; every motion rule respects `prefers-reduced-motion`.

## Elevation & Depth

Ambient, not interactive: cards carry a constant soft shadow at rest (`box-shadow: 0 2px 8px rgba(0,0,0,0.08)`) that signals "this is a distinct panel," and it does not change on hover. Depth is not used to imply clickability — clickability comes from the button-tier system instead.

The distinction that matters is **structure versus control**. A card, tile, chart panel or table container is structure: it holds content, it is not a target, and in this app none of them is ever wrapped in a link. A button, link, nav item, or table row is a control: it responds. Structure is static; controls respond. Getting this backwards is the single most common way a competent interface starts feeling generic — a page where every panel floats on hover is a page that has stopped telling you what is actually clickable.

Controls respond with **color, not levitation** wherever a tint will do: ghost and text buttons take a `--tint` fill and shift toward the accent on hover rather than moving. The filled primary and danger buttons keep their `translateY(-2px)` lift, because a filled button is unambiguously a target and the lift reads there as press-affordance rather than as decoration.

### Shadow Vocabulary
- **Card ambient** (`box-shadow: 0 2px 8px rgba(0,0,0,0.08)`): the default resting shadow for every card/panel.
- **Root shadow tokens** (`--shadow`, `--shadow-lg`): a slightly heavier two-layer variant reserved for larger/overlay surfaces (modals, dropdowns) that need to read as sitting above the page, not just as a distinct panel. In dark theme `--shadow-lg` adds a faint violet 1px ring (`0 0 0 1px rgba(157,132,255,0.06)`) because shadow alone barely separates surfaces on a dark ground.

### Named Rules
**The Structure-Not-Signal Rule.** Structure is static; controls respond. `.admin-card`, `.stat-tile`, `.chart-card`, `.table-card` and `.stat-card` have no hover state at all — no lift, no shadow change, no border shift. If a panel genuinely becomes clickable, it stops being structure and gets a real control inside it rather than becoming a giant button.

**The Tint-Before-Lift Rule.** A control's first move on hover is a `--tint` fill or an accent color shift. Movement is reserved for the filled tiers (primary, danger), where the target is already unmistakable.

## Shapes

Two radius tiers, used consistently rather than picked ad hoc, and both now tokenized so neither can drift: **`--radius-control` (6px)** for controls (buttons, inputs, small chips, bucket/filter boxes) and **`--radius-sm` (8px) / `--radius` (12px)** for containers (cards, panels, the subtopic-tree accordion). Pills (status badges, tags) are fully rounded (`border-radius: 999px`) — pill shape is reserved for small status/label chips, never stretched into a card radius.

### Named Rules
**The Two-Tier Radius Rule.** Every corner in the app is either a control corner or a container corner. Reach for the token, not a number; a hand-typed `border-radius` is how a third tier gets born.

## Components

### Buttons
Three tiers, always in this order of visual weight — this is the system's central legibility device, and the one most worth protecting from drift:
- **Primary** (`.admin-btn`): filled Study Violet, white text, `6px` radius. Exactly one per screen/section wherever possible — the thing the user is actually here to do (Save, Create, Publish-equivalent).
- **Danger** (`.admin-btn-danger`): same shape as primary, filled Alert Red instead. Reserved for destructive, confirm-gated actions (Delete) — never used just to "make something stand out."
- **Ghost** (`.admin-btn-ghost`): transparent fill, visible tinted border, dark (not muted) text. Secondary/navigational actions (Assign, Monitor, View). Must read as a real button at a glance — a border color too close to the page background (pure `--border` grey) reads as disabled and should be avoided; tint it toward the accent instead.
- **Text** (`.admin-btn-text`): the quietest tier, for rare/reversible utility actions (Archive, Duplicate, Back-navigation). No fill and no border at rest — but **full-strength ink**, never muted grey. It reads as quiet because it lacks a container, not because it is faint; muted grey text on a bare background is indistinguishable from a disabled control. On hover it takes a `--tint` fill and shifts to the accent, which is what proves it was a button all along.

**Icons on buttons:** consistent-stroke inline SVG (`stroke="currentColor"`, `stroke-width="2"`, `stroke-linecap/linejoin="round"`), one icon per action, never emoji or unicode arrows/glyphs (✕, →, 🎯, etc.) standing in for the icon.

### Pills / Badges
- **Style:** fully rounded, small, uppercase label text with slight letter-spacing.
- **State:** color comes from the semantic palette (emerald/amber/red/violet), never from the primary accent alone — a pill's color should tell you *what state* it represents at a glance.

### Cards / Containers
- **Corner Style:** 8–12px radius.
- **Background:** Paper White.
- **Shadow Strategy:** ambient card shadow (see Elevation & Depth); never a hover-triggered lift.
- **Border:** 1px Hairline.
- **Internal Padding:** ~1.25rem.

### Exam Mode (signature surface)

The timed test paper (`test_take.html`) is the one surface deliberately allowed to feel unlike the rest of the app — a student sits it under pressure, single-attempt, and the change of room is part of telling them so. **That difference is structural, not chromatic.** It is carried by:

- A sticky exam bar with a live pulsing "Test in progress" badge and a large countdown.
- A **2.1rem, weight-800, tabular-nums timer** — the loudest element on any screen in the product. It earns that by size and weight, never by gradient text, and it turns Alert Red in its final minutes so the change is a genuine event.
- A question navigator of circular dots carrying answered (emerald) and current (filled accent, `scale(1.08)`) state.
- A **760px single-question column** and the total absence of app chrome — no sidebar, no nav, nothing to click but the paper.
- A pre-submit review grid, and a sticky submit bar holding the surface's one filled action.
- A single accent-derived wash at the top of the page, over a faintly violet-tinted paper (`#f7f5fd`) — the only place in the app where the ground is not neutral.

Everything else inherits: Study Violet, the semantic set with its ink steps, Inter, the two-tier radius, the button treatment. The pulsing dot is the app's only permanently animating element and is switched off under `prefers-reduced-motion`.

**The Same Building Rule.** A surface may earn a different *composition* — different density, different chrome, a different ground. It never earns a different *palette*. If a screen needs to feel distinct, change what is on it and how it is arranged, not which violet it uses.

### Inputs / Fields
- **Style:** 1px Hairline border, Paper Grey fill, control radius (6px), ~`0.5rem 0.7rem` padding.
- **Focus:** border shifts to the accent with a soft accent-tinted ring; the global `:focus-visible` rule provides a 2px Study Violet outline at 2px offset on everything else.

### Tables
- **Style:** bordered container matching card radius, header row on Paper Grey, row-hover tint in the accent at very low opacity (a "this row is interactive" cue, not a color change). Rows are the exception to the Structure-Not-Signal Rule — a table row genuinely is a target, so it responds; the container around it does not.

## Do's and Don'ts

Guardrails grounded in this session's actual work on the Test Builder, generalized as the standard for the rest of the app.

### Do:
- **Do** keep the four-tier button hierarchy (primary / danger / ghost / text) legible — a tier may drop its fill and its border, but never its ink. Quietness is the absence of a container, never faint text.
- **Do** draw icons as small consistent-stroke SVGs matching the existing chevron/icon convention, even for one-off buttons.
- **Do** group related actions tightly and separate unrelated/destructive ones with a deliberately larger gap (and push destructive actions to the trailing edge of their row).
- **Do** keep shadows ambient/constant on cards; reserve hover treatments for things that are actually buttons, links, or table rows.
- **Do** reach for the token (`--radius-control`, `--tint`, `--surface-hover`, `--ease-out`) rather than retyping its value. Every one of these exists because the same literal was being repeated across files and drifting.
- **Do** use `--tint` for "the accent has touched this" states and `--surface-hover` for neutral row/icon-button hovers. They are not interchangeable: tint means selected or accent-active, surface-hover means merely pointed at.
- **Do** add new long-form reading surfaces to the Libertinus Serif world if reading is genuinely the job there — the serif is the reading experience's identity, not an accident.

### Don't:
- **Don't** use emoji or unicode glyphs (📄, 🎯, 🔴, ✕, ←, →, ⚠) as a substitute icon system — this is one of the most common "AI-generated UI" tells and directly undermines the "not AI slop" brief.
- **Don't** add a colored `border-left`/`border-right` accent bar to cards, alerts, or callouts as a decoration — another common AI-generated-UI tell; the existing HL-warning banner's amber left-border is a known instance to eventually revisit.
- **Don't** let a secondary/tertiary button's border or text color get close enough to the neutral background that it reads as disabled — this was the exact defect fixed on the Test Builder's action row and applies everywhere else the same button classes are used.
- **Don't** reach for a second "loud" filled button on the same row as the primary action — competing primaries defeat the one-accent hierarchy.
- **Don't** load a third typeface. Two families is the system. If a surface needs more presence, it gets Inter at a heavier weight and a larger size.
- **Don't** give a card, tile, or panel a hover lift. This was removed from all five card classes app-wide; re-adding it to one screen re-opens the drift.
- **Don't** redefine `--primary` inside a page-scoped `<style>` block. Surfaces inherit the accent; they don't fork it — earn distinctness through composition instead (see The Same Building Rule).
- **Don't** set small text in a saturated semantic hue. Use the ink step; the fill value is for backgrounds, borders and dots.
- **Don't** use gradient text. It failed hardest on the exam timer, where it made the single most important number on screen the least readable one.

### Known divergences (documented, not endorsed)

These exist in the code today and should be reconciled rather than copied:

- **`ee-exemplars.css` runs a separate visual world** — near-black navy grounds (`#070a13`), a crimson-rose gradient accent (`#ff4a6b`), and glow shadows (`--accent-glow`). No violet, no paper tones. Its typeface is now Inter, matching the rest of the app, but its palette remains its own.
- **`.btn-primary` / `.btn-secondary` use 135° gradient fills** (and `.btn-secondary` is green), predating the flat three-tier `.admin-btn-*` system that superseded them. New work uses the `.admin-btn-*` tiers.
- **The HL-warning banner's amber `border-left` accent bar** remains the one live instance of the decorative accent-bar pattern this document rules out.
