"""Unit tests for the multilingual WhatsApp presence parser."""
from datetime import datetime

import pytest

from src.whatsapp_beacon.presence import (
    LAST_SEEN,
    ONLINE,
    OTHER,
    TYPING,
    PresenceParser,
)


def make_parser(language='en', now=None):
    # Default reference clock is late in the day so "last seen today at HH:MM"
    # does not trip the future-time rollback heuristic.
    return PresenceParser(language=language, now=now or datetime(2026, 8, 14, 23, 0, 0))


def test_empty_text_is_other():
    snapshot = make_parser().parse('')
    assert snapshot.kind == OTHER
    assert snapshot.text == ''
    assert snapshot.last_seen is None
    assert snapshot.is_online is False


def test_none_text_is_other():
    snapshot = make_parser().parse(None)
    assert snapshot.kind == OTHER


def test_online_english():
    snapshot = make_parser().parse('online')
    assert snapshot.kind == ONLINE
    assert snapshot.is_online is True


def test_online_spanish():
    snapshot = make_parser(language='es').parse('en línea')
    assert snapshot.kind == ONLINE


def test_online_turkish():
    snapshot = make_parser(language='tr').parse('çevrimiçi')
    assert snapshot.kind == ONLINE


def test_typing_is_not_last_seen():
    snapshot = make_parser().parse('typing…')
    assert snapshot.kind == TYPING


def test_last_seen_today_english():
    snapshot = make_parser().parse('last seen today at 14:32')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2026-08-14 14:32:00'


def test_last_seen_yesterday_english():
    snapshot = make_parser().parse('last seen yesterday at 21:05')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2026-08-13 21:05:00'


def test_last_seen_plain_implies_today():
    snapshot = make_parser().parse('last seen at 09:15')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2026-08-14 09:15:00'


def test_last_seen_with_us_date():
    snapshot = make_parser().parse('last seen on 12/31/2025 at 23:59')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2025-12-31 23:59:00'


def test_last_seen_with_eu_date():
    snapshot = make_parser().parse('last seen on 31/12/2025 at 23:59')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2025-12-31 23:59:00'


def test_last_seen_with_iso_date():
    snapshot = make_parser().parse('last seen on 2025-12-31 at 08:00')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2025-12-31 08:00:00'


def test_last_seen_future_today_rolls_back_a_day():
    # Observed at 07:00, but status claims "today at 23:00" -> previous day.
    snapshot = make_parser(now=datetime(2026, 8, 14, 7, 0, 0)).parse('last seen today at 23:00')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2026-08-13 23:00:00'


def test_invalid_time_is_last_seen_without_parsed_value():
    snapshot = make_parser().parse('last seen today at 99:99')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen is None
    assert snapshot.text == 'last seen today at 99:99'


@pytest.mark.parametrize(
    'language,text,expected',
    [
        ('es', 'visto por última vez hoy a las 14:32', '2026-08-14 14:32:00'),
        ('es', 'visto por ultima vez ayer a las 21:05', '2026-08-13 21:05:00'),
        ('de', 'zuletzt online heute um 14:32', '2026-08-14 14:32:00'),
        ('de', 'zuletzt online gestern um 21:05', '2026-08-13 21:05:00'),
        ('fr', "vu en ligne aujourd'hui à 14:32", '2026-08-14 14:32:00'),
        ('fr', 'vue en ligne hier à 21:05', '2026-08-13 21:05:00'),
        ('it', 'visto online oggi alle 14:32', '2026-08-14 14:32:00'),
        ('it', 'visto online ieri alle 21:05', '2026-08-13 21:05:00'),
        ('pt', 'visto por último hoje às 14:32', '2026-08-14 14:32:00'),
        ('pt', 'visto por ultimo ontem às 21:05', '2026-08-13 21:05:00'),
        ('cat', 'vist per última vegada avui a les 14:32', '2026-08-14 14:32:00'),
        ('tr', 'son görülme bugün 14:32', '2026-08-14 14:32:00'),
    ],
)
def test_last_seen_multilingual(language, text, expected):
    snapshot = make_parser(language=language).parse(text)
    assert snapshot.kind == LAST_SEEN, f'expected last_seen for {text!r}'
    assert snapshot.last_seen == expected, text


def test_unrecognized_text_is_other_with_raw_text_preserved():
    snapshot = make_parser().parse('some totally new status wording here')
    assert snapshot.kind == OTHER
    assert snapshot.text == 'some totally new status wording here'


def test_unknown_language_falls_back_to_english():
    snapshot = make_parser(language='xx').parse('last seen today at 10:00')
    assert snapshot.kind == LAST_SEEN
    assert snapshot.last_seen == '2026-08-14 10:00:00'
