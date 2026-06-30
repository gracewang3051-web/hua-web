"""Neon Postgres connection pool."""
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Lazy-init connection pool
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise RuntimeError('DATABASE_URL not set')
        # Neon 用的 postgres:// 形式，psycopg2 也支持
        _pool = pool.SimpleConnectionPool(1, 10, dsn=db_url)
    return _pool

@contextmanager
def get_conn():
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)

def init_schema():
    """初始化表结构（首次部署时调用）"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            uuid TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            card_id TEXT NOT NULL,
            notebook TEXT NOT NULL,
            rating TEXT NOT NULL CHECK (rating IN ('know', 'fuzzy', 'unknow')),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_records_user ON records(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_records_card ON records(card_id);
        """)
        conn.commit()
        cur.close()

def upsert_user(uuid: str) -> int:
    """插入或获取 user_id。"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE uuid = %s", (uuid,))
        row = cur.fetchone()
        if row:
            user_id = row[0]
        else:
            cur.execute("INSERT INTO users (uuid) VALUES (%s) RETURNING id", (uuid,))
            user_id = cur.fetchone()[0]
            conn.commit()
        cur.close()
        return user_id

def record_answer(user_id: int, card_id: str, notebook: str, rating: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO records (user_id, card_id, notebook, rating) VALUES (%s, %s, %s, %s) RETURNING id, created_at",
            (user_id, card_id, notebook, rating)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return {"id": row[0], "created_at": row[1].isoformat()}

def get_user_stats(user_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # 总答题数 / 各档计数 / 唯一错题数
        cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE rating = 'know') AS know,
            COUNT(*) FILTER (WHERE rating = 'fuzzy') AS fuzzy,
            COUNT(*) FILTER (WHERE rating = 'unknow') AS unknow,
            COUNT(DISTINCT CASE WHEN rating IN ('fuzzy', 'unknow') THEN card_id END) AS wrong_cards
        FROM records WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        # 最近 7 天
        cur.execute("""
        SELECT DATE(created_at) AS day, COUNT(*) AS cnt
        FROM records WHERE user_id = %s AND created_at >= NOW() - INTERVAL '7 days'
        GROUP BY day ORDER BY day
        """, (user_id,))
        daily = [{"day": str(r['day']), "count": r['cnt']} for r in cur.fetchall()]
        # 按课统计
        cur.execute("""
        SELECT notebook, COUNT(*) AS cnt
        FROM records WHERE user_id = %s
        GROUP BY notebook ORDER BY cnt DESC
        """, (user_id,))
        by_notebook = [{"notebook": r['notebook'], "count": r['cnt']} for r in cur.fetchall()]
        cur.close()
        return {
            "total": row['total'] or 0,
            "know": row['know'] or 0,
            "fuzzy": row['fuzzy'] or 0,
            "unknow": row['unknow'] or 0,
            "wrong_cards": row['wrong_cards'] or 0,
            "daily_7d": daily,
            "by_notebook": by_notebook,
        }

def get_wrong_cards(user_id: int) -> list:
    """错题列表，按错题次数倒序。"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
        SELECT card_id, notebook, COUNT(*) FILTER (WHERE rating IN ('fuzzy', 'unknow')) AS wrong_count,
               MAX(created_at) AS last_wrong
        FROM records WHERE user_id = %s
        GROUP BY card_id, notebook
        HAVING COUNT(*) FILTER (WHERE rating IN ('fuzzy', 'unknow')) > COUNT(*) FILTER (WHERE rating = 'know')
        ORDER BY wrong_count DESC, last_wrong DESC
        LIMIT 200
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

def export_records_csv(user_id: int = None) -> str:
    import csv, io
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if user_id:
            cur.execute("""
            SELECT u.uuid, r.card_id, r.notebook, r.rating, r.created_at
            FROM records r JOIN users u ON r.user_id = u.id
            WHERE r.user_id = %s ORDER BY r.created_at DESC
            """, (user_id,))
        else:
            cur.execute("""
            SELECT u.uuid, r.card_id, r.notebook, r.rating, r.created_at
            FROM records r JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC LIMIT 10000
            """)
        rows = cur.fetchall()
        cur.close()
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=['uuid','card_id','notebook','rating','created_at'])
        w.writeheader()
        for r in rows:
            w.writerow({
                'uuid': r['uuid'],
                'card_id': r['card_id'],
                'notebook': r['notebook'],
                'rating': r['rating'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else '',
            })
        return buf.getvalue()

def admin_overview() -> dict:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COUNT(*) AS n FROM users")
        users_n = cur.fetchone()['n']
        cur.execute("SELECT COUNT(*) AS n FROM records")
        records_n = cur.fetchone()['n']
        cur.execute("""
        SELECT notebook, COUNT(*) AS cnt
        FROM records GROUP BY notebook ORDER BY cnt DESC
        """)
        by_notebook = [dict(r) for r in cur.fetchall()]
        cur.execute("""
        SELECT u.uuid, COUNT(r.id) AS cnt
        FROM users u LEFT JOIN records r ON r.user_id = u.id
        GROUP BY u.uuid ORDER BY cnt DESC LIMIT 20
        """)
        top_users = [dict(r) for r in cur.fetchall()]
        cur.execute("""
        SELECT card_id, COUNT(*) FILTER (WHERE rating IN ('fuzzy','unknow')) AS wrong,
               COUNT(*) AS total
        FROM records GROUP BY card_id
        HAVING COUNT(*) FILTER (WHERE rating IN ('fuzzy','unknow')) > 0
        ORDER BY wrong DESC LIMIT 20
        """)
        top_wrong = [dict(r) for r in cur.fetchall()]
        cur.close()
        return {
            'users': users_n,
            'records': records_n,
            'by_notebook': by_notebook,
            'top_users': top_users,
            'top_wrong': top_wrong,
        }
