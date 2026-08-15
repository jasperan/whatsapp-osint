from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .database import Database, compose_session_datetime


class AnalyticsDashboard:
    def __init__(self, db_path: str = 'data/victims_logs.db', output_file: str = 'analytics/index.html'):
        self.db_path = Path(db_path)
        self.output_file = Path(output_file)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _load_sessions(self) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []

        query = '''
            SELECT
                u.user_name,
                s.start_date,
                s.start_hour,
                s.start_minute,
                s.start_second,
                s.end_date,
                s.end_hour,
                s.end_minute,
                s.end_second,
                s.time_connected
            FROM Sessions s
            JOIN Users u ON s.user_id = u.id
            WHERE s.start_date IS NOT NULL
            ORDER BY s.start_date ASC, s.start_hour ASC, s.start_minute ASC, s.start_second ASC
        '''

        sessions: List[Dict[str, Any]] = []
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                start_dt = compose_session_datetime(row[1], row[2], row[3], row[4])
                in_progress = row[5] is None
                if in_progress:
                    end_dt = now
                else:
                    end_dt = compose_session_datetime(row[5], row[6], row[7], row[8])
                if row[9] not in (None, ''):
                    duration_seconds = int(float(row[9]))
                else:
                    duration_seconds = int(max((end_dt - start_dt).total_seconds(), 0))
                sessions.append({
                    'user_name': row[0],
                    'start_iso': start_dt.isoformat(),
                    'end_iso': end_dt.isoformat(),
                    'start_label': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_label': 'In progress' if in_progress else end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': start_dt.strftime('%Y-%m-%d'),
                    'hour': start_dt.hour,
                    'start_minutes': start_dt.hour * 60 + start_dt.minute,
                    'weekday_index': start_dt.weekday(),
                    'weekday_label': start_dt.strftime('%A'),
                    'duration_seconds': duration_seconds,
                    'in_progress': in_progress,
                })
        return sessions

    def _load_presence(self) -> List[Dict[str, Any]]:
        """Loads presence observations (oldest → newest), joined with contacts.

        Delegates to :meth:`Database.get_presence_history` so the query and
        row shape stay defined in exactly one place.
        """
        if not self.db_path.exists():
            return []
        return Database(str(self.db_path)).get_presence_history()

    @staticmethod
    def _regularity_score(sessions: List[Dict[str, Any]]) -> Optional[int]:
        """Estimates how predictable a contact's schedule is (0-100).

        Uses the first session start of each tracked day. The score is
        ``max(0, 100 - std / 3)`` where ``std`` is the standard deviation of
        daily first-start times in minutes: a 30-minute spread scores ~90,
        a 3-hour spread scores ~40, and anything past 5 hours scores 0.
        Fewer than two tracked days yields ``None`` (unknown).
        """
        first_times: Dict[str, int] = {}
        for session in sessions:
            date = session['date']
            if date in first_times:
                continue
            first_times[date] = session['start_minutes']

        if len(first_times) < 2:
            return None
        values = list(first_times.values())
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std_minutes = math.sqrt(variance)
        return int(max(0, round(100 - std_minutes / 3.0)))

    def build_payload(self) -> Dict[str, Any]:
        sessions = self._load_sessions()
        total_seconds = sum(session['duration_seconds'] for session in sessions)
        total_sessions = len(sessions)
        total_contacts = len({session['user_name'] for session in sessions})
        average_seconds = round(total_seconds / total_sessions) if total_sessions else 0
        longest_seconds = max((session['duration_seconds'] for session in sessions), default=0)

        daily_rollup: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'total_seconds': 0, 'session_count': 0})
        user_rollup: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                'user_name': '',
                'total_seconds': 0,
                'session_count': 0,
                'average_seconds': 0,
                'longest_seconds': 0,
                'last_seen': None,
            }
        )
        weekday_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hourly_heatmap = [[0 for _ in range(24)] for _ in range(7)]
        duration_buckets = {
            '<30 sec': 0,
            '30-120 sec': 0,
            '2-5 min': 0,
            '5-15 min': 0,
            '15+ min': 0,
        }

        for session in sessions:
            daily_rollup[session['date']]['total_seconds'] += session['duration_seconds']
            daily_rollup[session['date']]['session_count'] += 1

            user_entry = user_rollup[session['user_name']]
            user_entry['user_name'] = session['user_name']
            user_entry['total_seconds'] += session['duration_seconds']
            user_entry['session_count'] += 1
            user_entry['longest_seconds'] = max(user_entry['longest_seconds'], session['duration_seconds'])
            user_entry['last_seen'] = max(user_entry['last_seen'], session['end_iso']) if user_entry['last_seen'] else session['end_iso']

            hourly_heatmap[session['weekday_index']][session['hour']] += 1

            duration = session['duration_seconds']
            if duration < 30:
                duration_buckets['<30 sec'] += 1
            elif duration <= 120:
                duration_buckets['30-120 sec'] += 1
            elif duration <= 300:
                duration_buckets['2-5 min'] += 1
            elif duration <= 900:
                duration_buckets['5-15 min'] += 1
            else:
                duration_buckets['15+ min'] += 1

        users = sorted(
            (
                {
                    **data,
                    'average_seconds': round(data['total_seconds'] / data['session_count']) if data['session_count'] else 0,
                }
                for data in user_rollup.values()
            ),
            key=lambda item: (-item['total_seconds'], item['user_name'].lower()),
        )

        # Presence intelligence: per-contact last-seen evidence, observation
        # counts, and a schedule-regularity estimate derived from session starts.
        presence_list = self._load_presence()
        presence_trail = presence_list[-25:]
        latest_presence_label: Dict[str, str] = {}
        presence_counts: Dict[str, int] = {}
        for row in presence_list:
            name = row['user_name']
            presence_counts[name] = presence_counts.get(name, 0) + 1
            if row['status_kind'] == 'online':
                latest_presence_label[name] = f"Online {row['observed_at']}"
            elif row['status_kind'] == 'last_seen':
                if row.get('last_seen'):
                    latest_presence_label[name] = f"Last seen {row['last_seen']}"
                else:
                    latest_presence_label[name] = f"Last seen ~{row['observed_at']}"

        user_sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for session in sessions:
            user_sessions[session['user_name']].append(session)

        for user in users:
            name = user['user_name']
            user['presence_count'] = presence_counts.get(name, 0)
            if name in latest_presence_label:
                user['last_seen_label'] = latest_presence_label[name]
            elif user.get('last_seen'):
                user['last_seen_label'] = f"Last session {user['last_seen']}"
            else:
                user['last_seen_label'] = None
            user['regularity_score'] = self._regularity_score(user_sessions.get(name, []))
            user['active_days'] = len({session['date'] for session in user_sessions.get(name, [])})

        daily_activity = [
            {
                'date': date,
                'label': datetime.strptime(date, '%Y-%m-%d').strftime('%b %d'),
                'total_seconds': data['total_seconds'],
                'session_count': data['session_count'],
            }
            for date, data in sorted(daily_rollup.items())
        ]

        recent_sessions = sorted(sessions, key=lambda session: session['start_iso'], reverse=True)[:25]
        top_sessions = sorted(sessions, key=lambda session: session['duration_seconds'], reverse=True)[:10]

        busiest_hour = 0
        busiest_hour_count = 0
        for weekday in hourly_heatmap:
            for hour, count in enumerate(weekday):
                if count > busiest_hour_count:
                    busiest_hour = hour
                    busiest_hour_count = count

        return {
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'summary': {
                'total_sessions': total_sessions,
                'total_contacts': total_contacts,
                'total_seconds': total_seconds,
                'average_seconds': average_seconds,
                'longest_seconds': longest_seconds,
                'busiest_hour': busiest_hour,
                'busiest_hour_count': busiest_hour_count,
            },
            'users': users,
            'sessions': sessions,
            'daily_activity': daily_activity,
            'hourly_heatmap': [
                {
                    'day': weekday_labels[index],
                    'hours': hours,
                }
                for index, hours in enumerate(hourly_heatmap)
            ],
            'duration_buckets': [
                {'label': label, 'count': count}
                for label, count in duration_buckets.items()
            ],
            'recent_sessions': recent_sessions,
            'top_sessions': top_sessions,
            'presence_trail': presence_trail,
        }

    def export(self) -> Path:
        payload = self.build_payload()
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(self._render_html(payload), encoding='utf-8')
        return self.output_file

    def _render_html(self, payload: Dict[str, Any]) -> str:
        data_json = json.dumps(payload, ensure_ascii=False)
        template = Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
        return (
            template
            .replace('__GENERATED_AT__', payload['generated_at'])
            .replace('__DATA_JSON__', data_json)
        )
