"""Utilities for extracting and analyzing student feedback."""

import re
import json
from html.parser import HTMLParser


class BoldTextExtractor(HTMLParser):
    """Extract text wrapped in <b> or <strong> tags from HTML."""

    def __init__(self):
        super().__init__()
        self.bold_phrases = []
        self.current_bold = []
        self.in_bold = False

    def handle_starttag(self, tag, attrs):
        if tag in ('b', 'strong'):
            self.in_bold = True
            self.current_bold = []

    def handle_endtag(self, tag):
        if tag in ('b', 'strong') and self.in_bold:
            self.in_bold = False
            text = ''.join(self.current_bold).strip()
            if text:
                self.bold_phrases.append(text)
            self.current_bold = []

    def handle_data(self, data):
        if self.in_bold:
            self.current_bold.append(data)

    def extract(self, html_text):
        """Parse HTML and return list of bold phrases."""
        self.bold_phrases = []
        try:
            self.feed(html_text or '')
        except Exception:
            pass
        return self.bold_phrases


_MD_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")


def extract_bold_keywords(feedback_html):
    """Extract bold phrases (HTML <b>/<strong> or markdown **...**) and return as JSON list."""
    if not feedback_html:
        return "[]"
    extractor = BoldTextExtractor()
    phrases = extractor.extract(feedback_html)
    phrases.extend(m.strip() for m in _MD_BOLD_RE.findall(feedback_html))
    seen, unique = set(), []
    for phrase in phrases:
        key = phrase.lower()
        if phrase and key not in seen:
            seen.add(key)
            unique.append(phrase)
    return json.dumps(unique, ensure_ascii=False)


def store_feedback_insight(quiz_answer, source_text=None):
    """Extract and store feedback keywords from a quiz answer.

    By default reads the teacher's feedback; pass source_text to store
    insights from the provisional AI feedback instead (e.g. at submission,
    so every attempt — including retakes — records its weakness themes)."""
    from extensions import db
    from models import StudentFeedbackInsight

    text = source_text or quiz_answer.feedback
    if not text:
        return

    keywords = extract_bold_keywords(text)

    insight = StudentFeedbackInsight(
        answer_id=quiz_answer.id,
        student_id=quiz_answer.student_id,
        question_id=quiz_answer.question_id,
        feedback_text=text,
        extracted_keywords=keywords,
    )
    db.session.add(insight)
    db.session.commit()
