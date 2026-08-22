"""Drawn icons for the printable reports (test report and report card).

Two reasons this exists instead of emoji, and the second one is the reason it is
a shared module rather than a convention:

1. DESIGN.md: "Icons are drawn (consistent-stroke SVG), never emoji or unicode
   glyphs standing in for an icon system."
2. Performance. Emoji in a WeasyPrint document send the text shaper hunting the
   entire system font set for glyph coverage. On the test report that took PDF
   generation from 0.5s to 44s — an 89x penalty for a handful of decorative
   characters.

So: never put an emoji in report HTML. Add a path here instead.

Stroke geometry matches the app's existing icon convention (24x24 viewBox,
currentColor, stroke-width 2, round caps and joins).
"""

ICON_PATHS = {
    "chart": '<line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line>',
    "list": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line>',
    "comment": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>',
    "clock": '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>',
    "check": '<polyline points="20 6 9 17 4 12"></polyline>',
    "cross": '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>',
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>',
    "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"></path>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>',
    "book-open": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>',
    "pencil": '<path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"></path>',
    "award": '<circle cx="12" cy="8" r="6"></circle><polyline points="8.2 13.9 7 22 12 19 17 22 15.8 13.9"></polyline>',
    "search": '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.7" y2="16.7"></line>',
    "target": '<circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle>',
    "steps": '<polyline points="4 18 9 18 9 13 15 13 15 8 21 8"></polyline><line x1="21" y1="8" x2="21" y2="4"></line>',
}


def icon(name, size=16, extra_class=""):
    """Inline SVG markup for `name`, sized in px and safe to embed in report HTML."""
    return (
        f'<svg class="rpt-icon {extra_class}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICON_PATHS[name]}</svg>'
    )


# Shared CSS for icon alignment inside report documents. The right margin serves
# the hanging-indent list items; flex rows null it out and use `gap` instead.
ICON_CSS = ".rpt-icon { flex: 0 0 auto; vertical-align: -0.15em; margin-right: 0.4rem; }"
