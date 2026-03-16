from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


class AnalyticsDashboard:
    def __init__(self, db_path: str = 'database/victims_logs.db', output_file: str = 'analytics/index.html'):
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
              AND s.end_date IS NOT NULL
              AND s.time_connected IS NOT NULL
            ORDER BY s.start_date ASC, s.start_hour ASC, s.start_minute ASC, s.start_second ASC
        '''

        sessions: List[Dict[str, Any]] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                start_dt = datetime.strptime(
                    f"{row[1]} {row[2]}:{row[3]}:{row[4]}", '%Y-%m-%d %H:%M:%S'
                )
                end_dt = datetime.strptime(
                    f"{row[5]} {row[6]}:{row[7]}:{row[8]}", '%Y-%m-%d %H:%M:%S'
                )
                duration_seconds = int(float(row[9])) if row[9] not in (None, '') else int(max((end_dt - start_dt).total_seconds(), 0))
                sessions.append({
                    'user_name': row[0],
                    'start_iso': start_dt.isoformat(),
                    'end_iso': end_dt.isoformat(),
                    'start_label': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_label': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': start_dt.strftime('%Y-%m-%d'),
                    'hour': start_dt.hour,
                    'weekday_index': start_dt.weekday(),
                    'weekday_label': start_dt.strftime('%A'),
                    'duration_seconds': duration_seconds,
                })
        return sessions

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
            'generated_at': datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC'),
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
        }

    def export(self) -> Path:
        payload = self.build_payload()
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(self._render_html(payload), encoding='utf-8')
        return self.output_file

    def _render_html(self, payload: Dict[str, Any]) -> str:
        data_json = json.dumps(payload, ensure_ascii=False)
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WhatsApp Beacon Analytics</title>
  <style>
    :root {{
      --bg: #07111f;
      --bg-elevated: rgba(13, 27, 43, 0.82);
      --panel: rgba(12, 29, 47, 0.92);
      --panel-strong: rgba(10, 23, 36, 0.98);
      --line: rgba(119, 220, 255, 0.18);
      --line-strong: rgba(119, 220, 255, 0.35);
      --text: #f3f8ff;
      --muted: #95a7c1;
      --accent: #6cf1ff;
      --accent-2: #8bffb5;
      --accent-3: #ffd166;
      --danger: #ff7a90;
      --shadow: 0 24px 60px rgba(0, 0, 0, 0.38);
      --radius: 24px;
      --radius-sm: 16px;
      --display: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      --body: "Trebuchet MS", "Segoe UI", sans-serif;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; min-height: 100%; }}
    body {{
      font-family: var(--body);
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(108, 241, 255, 0.18), transparent 32%),
        radial-gradient(circle at top right, rgba(139, 255, 181, 0.16), transparent 28%),
        linear-gradient(180deg, #07111f 0%, #091827 52%, #050b14 100%);
      background-attachment: fixed;
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: radial-gradient(circle at center, black 25%, transparent 92%);
      opacity: 0.5;
    }}

    .shell {{
      width: min(1380px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      padding: 32px;
      border: 1px solid var(--line);
      border-radius: calc(var(--radius) + 6px);
      background: linear-gradient(140deg, rgba(8, 20, 34, 0.96), rgba(7, 17, 31, 0.84));
      box-shadow: var(--shadow);
      margin-bottom: 24px;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -80px -120px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(108, 241, 255, 0.28), transparent 70%);
      filter: blur(6px);
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(108, 241, 255, 0.22);
      background: rgba(108, 241, 255, 0.08);
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
    }}

    h1 {{
      margin: 18px 0 12px;
      font-family: var(--display);
      font-size: clamp(2.6rem, 5vw, 4.7rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
      max-width: 10ch;
    }}

    .hero-copy {{
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.9fr);
      gap: 24px;
      position: relative;
      z-index: 1;
    }}

    .hero p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      font-size: 1.02rem;
      max-width: 64ch;
    }}

    .hero-meta {{
      align-self: end;
      padding: 18px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--line);
      background: rgba(10, 23, 36, 0.76);
      backdrop-filter: blur(16px);
    }}

    .hero-meta strong {{ display: block; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--accent-2); margin-bottom: 8px; }}
    .hero-meta span {{ color: var(--text); }}

    .controls {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      padding: 18px 20px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--line);
      background: var(--bg-elevated);
      backdrop-filter: blur(14px);
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}

    label {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}

    select {{
      min-width: 220px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line-strong);
      background: rgba(5, 11, 20, 0.7);
      color: var(--text);
      font: inherit;
      outline: none;
    }}

    .controls-copy {{
      max-width: 56ch;
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.96rem;
    }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .metric-card, .panel {{
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(13, 27, 43, 0.94), rgba(8, 18, 30, 0.96));
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .metric-card {{ padding: 20px; min-height: 148px; display: flex; flex-direction: column; justify-content: space-between; }}
    .metric-card .label {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.75rem; }}
    .metric-card .value {{ font-family: var(--display); font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1; margin: 14px 0 10px; }}
    .metric-card .hint {{ color: var(--muted); font-size: 0.92rem; }}

    .grid {{
      display: grid;
      grid-template-columns: 1.35fr 0.95fr;
      gap: 20px;
      margin-bottom: 20px;
    }}

    .panel {{ padding: 24px; }}
    .panel h2 {{ margin: 0 0 8px; font-family: var(--display); font-size: 1.7rem; letter-spacing: -0.03em; }}
    .panel p.lead {{ margin: 0 0 18px; color: var(--muted); line-height: 1.6; }}

    .bars {{ display: flex; align-items: end; gap: 12px; min-height: 300px; }}
    .bar-column {{ flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: end; gap: 10px; }}
    .bar-track {{
      position: relative;
      height: 260px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
      border: 1px solid rgba(255,255,255,0.04);
      display: flex;
      align-items: end;
      overflow: hidden;
    }}
    .bar-fill {{
      width: 100%;
      border-radius: 16px 16px 0 0;
      background: linear-gradient(180deg, var(--accent), rgba(108, 241, 255, 0.28));
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }}
    .bar-meta {{ font-size: 0.85rem; color: var(--muted); }}
    .bar-meta strong {{ display: block; color: var(--text); font-size: 0.95rem; margin-bottom: 3px; }}

    .heatmap {{ display: grid; grid-template-columns: 120px repeat(24, minmax(0, 1fr)); gap: 8px; align-items: center; }}
    .heatmap-header, .heatmap-label {{ color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    .heatmap-cell {{
      aspect-ratio: 1 / 1;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.05);
      background: rgba(255,255,255,0.03);
      position: relative;
    }}
    .heatmap-cell span {{
      position: absolute;
      inset: auto 6px 6px auto;
      font-size: 0.68rem;
      color: rgba(255,255,255,0.7);
    }}

    .leaderboard {{ display: grid; gap: 14px; }}
    .leaderboard-item {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 14px;
      align-items: center;
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.05);
      background: rgba(255,255,255,0.03);
    }}
    .leaderboard-rank {{
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-weight: 700;
      color: var(--bg);
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }}
    .leaderboard-item strong {{ display: block; font-size: 1rem; margin-bottom: 4px; }}
    .leaderboard-item span {{ color: var(--muted); font-size: 0.9rem; }}
    .leaderboard-stat {{ text-align: right; }}
    .leaderboard-stat strong {{ display: block; font-size: 1.15rem; }}
    .leaderboard-stat span {{ color: var(--muted); font-size: 0.85rem; }}

    .bucket-list {{ display: grid; gap: 12px; }}
    .bucket-row {{ display: grid; grid-template-columns: 130px 1fr auto; gap: 12px; align-items: center; }}
    .bucket-label {{ color: var(--muted); font-size: 0.9rem; }}
    .bucket-track {{ height: 14px; border-radius: 999px; background: rgba(255,255,255,0.05); overflow: hidden; }}
    .bucket-fill {{ height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent-3), rgba(255, 209, 102, 0.24)); }}
    .bucket-value {{ color: var(--text); font-size: 0.9rem; font-weight: 700; }}

    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    th {{ color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.12em; }}
    td {{ color: var(--text); font-size: 0.94rem; }}
    td.muted {{ color: var(--muted); }}

    .empty-state {{
      margin: 20px 0 0;
      padding: 22px;
      border-radius: 18px;
      border: 1px dashed rgba(255,255,255,0.1);
      color: var(--muted);
      background: rgba(255,255,255,0.02);
      line-height: 1.7;
    }}

    @media (max-width: 1100px) {{
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
      .hero-copy {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 760px) {{
      .shell {{ width: min(100vw - 20px, 100%); }}
      .hero, .panel {{ padding: 20px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .bars {{ gap: 8px; overflow-x: auto; padding-bottom: 8px; }}
      .bar-column {{ min-width: 84px; }}
      .heatmap {{ grid-template-columns: 88px repeat(24, 22px); overflow-x: auto; padding-bottom: 8px; }}
      .bucket-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">OSINT Analytics</span>
      <div class="hero-copy">
        <div>
          <h1>WhatsApp Beacon Analytics</h1>
          <p>
            A forensic-style dashboard for online session history. Filter by contact, scan burst windows,
            spot daily patterns, and review the exact session cadence without leaving a single static file.
          </p>
        </div>
        <div class="hero-meta">
          <strong>Generated</strong>
          <span id="generated-at">{payload['generated_at']}</span>
        </div>
      </div>
    </section>

    <section class="controls">
      <label>
        Contact filter
        <select id="user-filter"></select>
      </label>
      <div class="controls-copy" id="controls-copy">
        Use the filter to isolate one contact or keep the whole dataset in view. The charts below recompute instantly.
      </div>
    </section>

    <section class="metrics" id="metrics"></section>

    <section class="grid">
      <article class="panel">
        <h2>Daily activity arc</h2>
        <p class="lead">Total online time by day. This makes streaks, dead zones, and high-intensity bursts obvious fast.</p>
        <div class="bars" id="daily-bars"></div>
      </article>
      <article class="panel">
        <h2>Contact leaderboard</h2>
        <p class="lead">Who dominates the dataset, who shows up rarely, and who racks up the longest sessions.</p>
        <div class="leaderboard" id="leaderboard"></div>
      </article>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Weekly heatmap</h2>
        <p class="lead">Session starts mapped across weekdays and hours. Dense cells flag reliable behavior windows.</p>
        <div class="heatmap" id="heatmap"></div>
      </article>
      <article class="panel">
        <h2>Session duration mix</h2>
        <p class="lead">Short pings and long hangs side by side, bucketed for quick pattern recognition.</p>
        <div class="bucket-list" id="duration-buckets"></div>
      </article>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Recent sessions</h2>
        <p class="lead">The latest completed sessions, with full timestamps and durations.</p>
        <div id="recent-sessions"></div>
      </article>
      <article class="panel">
        <h2>Longest sessions</h2>
        <p class="lead">Top sessions by duration. Useful when you want the outliers instead of the averages.</p>
        <div id="top-sessions"></div>
      </article>
    </section>
  </main>

  <script>
    const dashboardData = {data_json};
    const state = {{ user: 'all' }};

    const byId = (id) => document.getElementById(id);

    function formatDuration(totalSeconds) {{
      if (!totalSeconds) return '0 sec';
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      const parts = [];
      if (hours) parts.push(`${{hours}}h`);
      if (minutes) parts.push(`${{minutes}}m`);
      if (seconds || parts.length === 0) parts.push(`${{seconds}}s`);
      return parts.join(' ');
    }}

    function formatHour(hour) {{
      return `${{String(hour).padStart(2, '0')}}:00`;
    }}

    function buildView(sessions) {{
      const totalSeconds = sessions.reduce((sum, session) => sum + session.duration_seconds, 0);
      const totalSessions = sessions.length;
      const averageSeconds = totalSessions ? Math.round(totalSeconds / totalSessions) : 0;
      const longestSeconds = sessions.reduce((max, session) => Math.max(max, session.duration_seconds), 0);
      const uniqueUsers = [...new Set(sessions.map((session) => session.user_name))];

      const dailyMap = new Map();
      const userMap = new Map();
      const heatmap = Array.from({{ length: 7 }}, () => Array(24).fill(0));
      const buckets = [
        {{ label: '<30 sec', count: 0 }},
        {{ label: '30-120 sec', count: 0 }},
        {{ label: '2-5 min', count: 0 }},
        {{ label: '5-15 min', count: 0 }},
        {{ label: '15+ min', count: 0 }},
      ];

      sessions.forEach((session) => {{
        const day = dailyMap.get(session.date) || {{ date: session.date, label: session.date.slice(5), total_seconds: 0, session_count: 0 }};
        day.total_seconds += session.duration_seconds;
        day.session_count += 1;
        dailyMap.set(session.date, day);

        const user = userMap.get(session.user_name) || {{ user_name: session.user_name, total_seconds: 0, session_count: 0, longest_seconds: 0, last_seen: null }};
        user.total_seconds += session.duration_seconds;
        user.session_count += 1;
        user.longest_seconds = Math.max(user.longest_seconds, session.duration_seconds);
        user.last_seen = !user.last_seen || session.end_iso > user.last_seen ? session.end_iso : user.last_seen;
        userMap.set(session.user_name, user);

        heatmap[session.weekday_index][session.hour] += 1;

        if (session.duration_seconds < 30) buckets[0].count += 1;
        else if (session.duration_seconds <= 120) buckets[1].count += 1;
        else if (session.duration_seconds <= 300) buckets[2].count += 1;
        else if (session.duration_seconds <= 900) buckets[3].count += 1;
        else buckets[4].count += 1;
      }});

      const users = [...userMap.values()]
        .map((user) => ({{ ...user, average_seconds: user.session_count ? Math.round(user.total_seconds / user.session_count) : 0 }}))
        .sort((left, right) => right.total_seconds - left.total_seconds || left.user_name.localeCompare(right.user_name));

      let busiestHour = 0;
      let busiestHourCount = 0;
      heatmap.forEach((weekday) => weekday.forEach((count, hour) => {{
        if (count > busiestHourCount) {{
          busiestHourCount = count;
          busiestHour = hour;
        }}
      }}));

      return {{
        summary: {{
          total_sessions: totalSessions,
          total_contacts: uniqueUsers.length,
          total_seconds: totalSeconds,
          average_seconds: averageSeconds,
          longest_seconds: longestSeconds,
          busiest_hour: busiestHour,
          busiest_hour_count: busiestHourCount,
        }},
        daily_activity: [...dailyMap.values()].sort((left, right) => left.date.localeCompare(right.date)),
        users,
        hourly_heatmap: dashboardData.hourly_heatmap.map((entry, index) => ({{ day: entry.day, hours: heatmap[index] }})),
        duration_buckets: buckets,
        recent_sessions: [...sessions].sort((left, right) => right.start_iso.localeCompare(left.start_iso)).slice(0, 25),
        top_sessions: [...sessions].sort((left, right) => right.duration_seconds - left.duration_seconds).slice(0, 10),
      }};
    }}

    function renderMetrics(summary) {{
      const metrics = [
        ['Sessions logged', summary.total_sessions, summary.total_sessions ? 'Completed, closed sessions only' : 'No finished sessions yet'],
        ['Contacts tracked', summary.total_contacts, summary.total_contacts ? 'Unique contacts in this filtered view' : 'Run the tracker to collect contacts'],
        ['Total online time', formatDuration(summary.total_seconds), 'Accumulated across the current filter'],
        ['Average session', formatDuration(summary.average_seconds), 'Mean duration per session'],
        ['Busiest hour', `${{formatHour(summary.busiest_hour)}}`, summary.busiest_hour_count ? `${{summary.busiest_hour_count}} session starts` : 'No repeated activity yet'],
      ];

      byId('metrics').innerHTML = metrics.map(([label, value, hint]) => `
        <article class="metric-card">
          <div class="label">${{label}}</div>
          <div class="value">${{value}}</div>
          <div class="hint">${{hint}}</div>
        </article>
      `).join('');
    }}

    function renderDailyBars(dailyActivity) {{
      if (!dailyActivity.length) {{
        byId('daily-bars').innerHTML = '<div class="empty-state">No closed sessions yet. Keep the tracker running, then regenerate analytics.</div>';
        return;
      }}

      const maxSeconds = Math.max(...dailyActivity.map((entry) => entry.total_seconds), 1);
      byId('daily-bars').innerHTML = dailyActivity.map((entry) => {{
        const height = Math.max(14, Math.round((entry.total_seconds / maxSeconds) * 100));
        return `
          <div class="bar-column">
            <div class="bar-track">
              <div class="bar-fill" style="height: ${{height}}%;"></div>
            </div>
            <div class="bar-meta">
              <strong>${{entry.label}}</strong>
              ${{formatDuration(entry.total_seconds)}} · ${{entry.session_count}} session${{entry.session_count === 1 ? '' : 's'}}
            </div>
          </div>
        `;
      }}).join('');
    }}

    function renderLeaderboard(users) {{
      if (!users.length) {{
        byId('leaderboard').innerHTML = '<div class="empty-state">No contact activity yet. Once sessions land in the database, the ranking shows who dominates the dataset.</div>';
        return;
      }}

      byId('leaderboard').innerHTML = users.slice(0, 6).map((user, index) => `
        <div class="leaderboard-item">
          <div class="leaderboard-rank">${{index + 1}}</div>
          <div>
            <strong>${{user.user_name}}</strong>
            <span>${{user.session_count}} session${{user.session_count === 1 ? '' : 's'}} · avg ${{formatDuration(user.average_seconds)}}</span>
          </div>
          <div class="leaderboard-stat">
            <strong>${{formatDuration(user.total_seconds)}}</strong>
            <span>Longest ${{formatDuration(user.longest_seconds)}}</span>
          </div>
        </div>
      `).join('');
    }}

    function renderHeatmap(rows) {{
      if (!rows.some((row) => row.hours.some((value) => value > 0))) {{
        byId('heatmap').innerHTML = '<div class="empty-state">The heatmap comes alive after a few days of tracking. Right now there is not enough finished activity to paint a pattern.</div>';
        return;
      }}

      const maxValue = Math.max(...rows.flatMap((row) => row.hours), 1);
      const header = ['<div></div>', ...Array.from({{ length: 24 }}, (_, hour) => `<div class="heatmap-header">${{String(hour).padStart(2, '0')}}</div>`)].join('');
      const body = rows.map((row) => `
        <div class="heatmap-label">${{row.day}}</div>
        ${{row.hours.map((value) => {{
          const strength = value ? value / maxValue : 0;
          const background = value
            ? `linear-gradient(180deg, rgba(108, 241, 255, ${{0.18 + strength * 0.62}}), rgba(139, 255, 181, ${{0.12 + strength * 0.4}}))`
            : 'rgba(255,255,255,0.03)';
          return `<div class="heatmap-cell" style="background:${{background}}; box-shadow:${{value ? `0 0 0 1px rgba(108,241,255,${{0.12 + strength * 0.2}}), inset 0 1px 0 rgba(255,255,255,0.12)` : 'none'}}"><span>${{value || ''}}</span></div>`;
        }}).join('')}}
      `).join('');
      byId('heatmap').innerHTML = header + body;
    }}

    function renderBuckets(buckets) {{
      const maxCount = Math.max(...buckets.map((bucket) => bucket.count), 1);
      byId('duration-buckets').innerHTML = buckets.map((bucket) => `
        <div class="bucket-row">
          <div class="bucket-label">${{bucket.label}}</div>
          <div class="bucket-track"><div class="bucket-fill" style="width: ${{Math.max((bucket.count / maxCount) * 100, bucket.count ? 10 : 0)}}%;"></div></div>
          <div class="bucket-value">${{bucket.count}}</div>
        </div>
      `).join('');
    }}

    function renderTable(containerId, rows) {{
      const container = byId(containerId);
      if (!rows.length) {{
        container.innerHTML = '<div class="empty-state">Nothing to show yet for this view.</div>';
        return;
      }}

      container.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Contact</th>
              <th>Started</th>
              <th>Ended</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            ${{rows.map((session) => `
              <tr>
                <td>${{session.user_name}}</td>
                <td class="muted">${{session.start_label}}</td>
                <td class="muted">${{session.end_label}}</td>
                <td>${{formatDuration(session.duration_seconds)}}</td>
              </tr>
            `).join('')}}
          </tbody>
        </table>
      `;
    }}

    function render(view) {{
      renderMetrics(view.summary);
      renderDailyBars(view.daily_activity);
      renderLeaderboard(view.users);
      renderHeatmap(view.hourly_heatmap);
      renderBuckets(view.duration_buckets);
      renderTable('recent-sessions', view.recent_sessions);
      renderTable('top-sessions', view.top_sessions);

      const scopeLabel = state.user === 'all' ? 'the full dataset' : `only ${{state.user}}`;
      byId('controls-copy').textContent = `You are viewing ${{scopeLabel}}. The cards and charts below are recalculated live inside this static report.`;
    }}

    function populateFilter() {{
      const filter = byId('user-filter');
      filter.innerHTML = ['<option value="all">All contacts</option>', ...dashboardData.users.map((user) => `<option value="${{user.user_name}}">${{user.user_name}}</option>`)].join('');
      filter.addEventListener('change', (event) => {{
        state.user = event.target.value;
        const sessions = state.user === 'all'
          ? dashboardData.sessions
          : dashboardData.sessions.filter((session) => session.user_name === state.user);
        render(buildView(sessions));
      }});
    }}

    populateFilter();
    render(buildView(dashboardData.sessions));
  </script>
</body>
</html>
'''
