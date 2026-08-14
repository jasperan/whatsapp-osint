"""Parsing of WhatsApp Web presence / status strings.

WhatsApp Web exposes a contact's current presence in the chat header and in
the sidebar subtitles. Typical values look like::

    online
    typing…
    last seen today at 14:32
    last seen yesterday at 21:05
    last seen at 14:32                  (older builds, implies today)
    last seen on 31/12/2025 at 23:59    (EU / other locales)
    last seen on 12/31/2025 at 23:59    (US locale)

The classic WhatsApp Beacon only records *online* blocks. This module turns
the status *text* into structured snapshots so the tool can passively record
"last seen" evidence — the moments between sessions when a contact was active
but not currently online.

The parser is deliberately best-effort: it understands a curated set of
languages and date layouts, and it always preserves the raw text, so a new
WhatsApp wording degrades to ``other`` instead of silently dropping data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Status kinds emitted by PresenceParser.
ONLINE = 'online'
LAST_SEEN = 'last_seen'
TYPING = 'typing'
OTHER = 'other'

# Mirrors beacon.ONLINE_STATUS so the parser never drifts from the tracker.
ONLINE_WORDS: Dict[str, str] = {
    'en': 'online',
    'de': 'online',
    'pt': 'online',
    'es': 'en línea',
    'fr': 'en ligne',
    'it': 'in linea',
    'cat': 'en línia',
    'tr': 'çevrimiçi',
}

# Localized "last seen" stems (as they appear in WhatsApp Web).
# Accented vowels are matched explicitly so 'última' and 'último' parse.
LAST_SEEN_STEMS: Dict[str, str] = {
    'en': 'last seen',
    'es': r'visto por (?:u|ú)ltima vez',
    'de': 'zuletzt online',
    'fr': r'vu(?:e)? en ligne|derni[eè]re connexion',
    'it': r'visto online|ultimo accesso',
    'pt': r'visto por (?:u|ú)ltimo',
    'tr': r'son g[oö]r[üu]lme',
    'cat': r'vist per (?:u|ú)ltima vegada',
}

TODAY_WORDS: Dict[str, str] = {
    'en': 'today',
    'es': 'hoy',
    'de': 'heute',
    'fr': r"aujourd'hui",
    'it': 'oggi',
    'pt': 'hoje',
    'tr': 'bugün',
    'cat': 'avui',
}

YESTERDAY_WORDS: Dict[str, str] = {
    'en': 'yesterday',
    'es': 'ayer',
    'de': 'gestern',
    'fr': 'hier',
    'it': 'ieri',
    'pt': 'ontem',
    'tr': 'dün',
    'cat': 'ahir',
}

# Substrings that indicate active typing / recording states.
_TYPING_MARKERS = (
    'typing',
    'escribiendo',
    'grabando',
    'recording',
    'digitando',
    'yazıyor',
    'yaziyor',
    'écrit',
    'digitando…',
)

_TIME_RE = re.compile(r'(?<!\d)(\d{1,2}):(\d{2})(?!\d)')

# Date layouts tried for "last seen on <DATE> at HH:MM".
_DATE_FORMATS = (
    '%Y-%m-%d',
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%d-%m-%Y',
    '%m-%d-%Y',
    '%d.%m.%Y',
    '%Y/%m/%d',
)


@dataclass
class PresenceSnapshot:
    """A parsed presence observation.

    ``kind`` is one of ``online``, ``last_seen``, ``typing``, ``other``.
    ``last_seen`` carries the parsed local datetime as ``%Y-%m-%d %H:%M:%S``
    when ``kind == last_seen`` (it is also populated for the plain / no-anchor
    forms when a time of day could be extracted). ``text`` is the raw status
    string, always preserved.
    """

    kind: str
    text: str
    last_seen: Optional[str] = None

    @property
    def is_online(self) -> bool:
        return self.kind == ONLINE


class PresenceParser:
    """Parses one presence string into a :class:`PresenceSnapshot`.

    ``now`` is injectable so tests can pin the reference clock. The language
    follows the tracker's ``ONLINE_STATUS`` keys (``en``, ``es``, ``de``,
    ``fr``, ``it``, ``pt``, ``cat``, ``tr``); unknown languages fall back to
    English wording.
    """

    def __init__(self, language: str = 'en', now: Optional[datetime] = None) -> None:
        self.language = (language or 'en').lower()
        self.now = now or datetime.now()
        self._stem = re.compile(
            LAST_SEEN_STEMS.get(self.language, LAST_SEEN_STEMS['en']),
            re.IGNORECASE,
        )
        self._today = re.compile(
            TODAY_WORDS.get(self.language, TODAY_WORDS['en']),
            re.IGNORECASE,
        )
        self._yesterday = re.compile(
            YESTERDAY_WORDS.get(self.language, YESTERDAY_WORDS['en']),
            re.IGNORECASE,
        )

    def parse(self, raw_text: Optional[str]) -> PresenceSnapshot:
        text = (raw_text or '').strip()
        if not text:
            return PresenceSnapshot(kind=OTHER, text='')

        lowered = text.lower()

        # Check the localized "last seen" stem first: texts like German
        # "zuletzt online heute um 14:32" contain the word "online" yet
        # describe a past presence, not a current one.
        if self._stem.search(lowered):
            return self._parse_last_seen(text, lowered)

        if self._is_online(lowered):
            return PresenceSnapshot(kind=ONLINE, text=text)

        if self._is_typing(lowered):
            return PresenceSnapshot(kind=TYPING, text=text)

        return PresenceSnapshot(kind=OTHER, text=text)

    # -- helpers ----------------------------------------------------------

    def _is_online(self, lowered: str) -> bool:
        word = ONLINE_WORDS.get(self.language, ONLINE_WORDS['en']).lower()
        if word in lowered:
            return True
        # Generic fallback: bare "online" appears in every locale.
        return bool(re.search(r'(^|[^a-z])online([^a-z]|$)', lowered))

    def _is_typing(self, lowered: str) -> bool:
        return any(marker in lowered for marker in _TYPING_MARKERS)

    def _parse_last_seen(self, text: str, lowered: str) -> PresenceSnapshot:
        anchor = self._resolve_anchor(lowered)
        date_match = self._resolve_on_date(lowered)
        time_match = _TIME_RE.search(text)

        if not time_match:
            return PresenceSnapshot(kind=LAST_SEEN, text=text)

        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        if hour > 23 or minute > 59:
            return PresenceSnapshot(kind=LAST_SEEN, text=text)

        base = date_match or anchor
        candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # "last seen today at 23:00" observed at 07:00 means the clock on the
        # status refers to the previous day.
        if candidate > self.now + timedelta(minutes=5):
            candidate -= timedelta(days=1)

        return PresenceSnapshot(
            kind=LAST_SEEN,
            text=text,
            last_seen=candidate.strftime('%Y-%m-%d %H:%M:%S'),
        )

    def _resolve_anchor(self, lowered: str) -> datetime:
        today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self._yesterday.search(lowered):
            return today - timedelta(days=1)
        return today

    def _resolve_on_date(self, lowered: str) -> Optional[datetime]:
        """Extract a concrete date from 'last seen on <DATE> at …'.

        Date layouts vary by locale; a handful of common ones are tried. If no
        date parses, the day anchor (today/yesterday) or plain today is used.
        """
        # Find the "on"/localized date introducer, then the digits before the time.
        on_word = {
            'en': 'on', 'es': 'el', 'de': 'am', 'fr': 'le',
            'it': 'il', 'pt': 'em', 'tr': None, 'cat': None,
        }.get(self.language)
        if not on_word:
            return None
        pattern = re.compile(
            r'\b' + re.escape(on_word) + r'\s+([0-9]{1,4}[./\-][0-9]{1,2}[./\-][0-9]{1,4})',
            re.IGNORECASE,
        )
        match = pattern.search(lowered)
        if not match:
            return None
        raw_date = match.group(1)
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(raw_date, fmt)
            except ValueError:
                continue
        return None
