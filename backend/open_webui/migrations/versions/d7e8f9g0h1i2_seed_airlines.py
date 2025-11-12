"""Seed airline table with predefined codes and names

Revision ID: d7e8f9g0h1i2
Revises: c5d6e7f8a9b0
Create Date: 2025-11-12 16:40:00.000000
"""

import uuid

from alembic import op
import sqlalchemy as sa


revision = "d7e8f9g0h1i2"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


AIRLINES = [
    ("HB", "大灣區航空"),
    ("CX", "國泰航空"),
    ("HX", "香港航空"),
    ("UO", "香港快運"),
    ("CA", "中國國際航空"),
    ("MU", "中國東方航空"),
    ("CZ", "中國南方航空"),
    ("CI", "中華航空"),
    ("BR", "長榮航空"),
    ("FM", "上海航空"),
    ("SC", "山東航空"),
    ("3U", "四川航空"),
    ("MF", "廈門航空"),
    ("HU", "海南航空"),
    ("HO", "吉祥航空"),
    ("9C", "春秋航空"),
    ("AE", "華夏航空"),
    ("AK", "亞洲航空"),
    ("FD", "泰國亞洲航空"),
    ("Z2", "菲律賓亞洲航空"),
    ("MH", "馬來西亞航空"),
    ("OD", "巴迪航空"),
    ("GA", "印尼鷹航"),
    ("AI", "印度航空"),
    ("6E", "靛藍航空"),
    ("JL", "日本航空"),
    ("NH", "全日空"),
    ("OZ", "韓亞航空"),
    ("KE", "大韓航空"),
    ("LJ", "真航空"),
    ("7C", "濟州航空"),
    ("ZE", "東海航空"),
    ("BX", "釜山航空"),
    ("RS", "首爾航空"),
    ("SQ", "新加坡航空"),
    ("TR", "酷航"),
    ("TG", "泰國航空"),
    ("PG", "曼谷航空"),
    ("VN", "越南航空"),
    ("VJ", "越捷航空"),
    ("BI", "皇家汶萊航空"),
    ("PR", "菲律賓航空"),
    ("5J", "宿霧太平洋航空"),
    ("EK", "阿聯酋航空"),
    ("EY", "阿提哈德航空"),
    ("QR", "卡達航空"),
    ("TK", "土耳其航空"),
    ("SU", "俄羅斯航空"),
    ("AF", "法國航空"),
    ("KL", "荷蘭皇家航空"),
    ("BA", "英國航空"),
    ("AY", "芬蘭航空"),
    ("LX", "瑞士國際航空"),
    ("VS", "維珍航空"),
    ("LH", "漢莎航空"),
    ("AC", "加拿大航空"),
    ("AA", "美國航空"),
    ("UA", "聯合航空"),
    ("DL", "達美航空"),
    ("NZ", "紐西蘭航空"),
    ("QF", "澳洲航空"),
    ("FJ", "斐濟航空"),
    ("LY", "以色列航空"),
    ("MS", "埃及航空"),
    ("ET", "衣索比亞航空"),
    ("MK", "毛里求斯航空"),
    ("SA", "南非航空"),
    ("RJ", "皇家約旦航空"),
]


def upgrade():
    conn = op.get_bind()
    for code, name in AIRLINES:
        result = conn.execute(
            sa.text(
                "SELECT airline_id FROM airline WHERE code = :code OR name = :name"
            ),
            {"code": code, "name": name},
        ).fetchone()
        if result:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO airline (airline_id, code, name, created_at, updated_at)
                VALUES (:airline_id, :code, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "airline_id": str(uuid.uuid4()),
                "code": code,
                "name": name,
            },
        )


def downgrade():
    conn = op.get_bind()
    codes = [code for code, _ in AIRLINES]
    if not codes:
        return

    placeholders = ", ".join(f":code_{i}" for i in range(len(codes)))
    params = {f"code_{i}": code for i, code in enumerate(codes)}
    conn.execute(
        sa.text(f"DELETE FROM airline WHERE code IN ({placeholders})"),
        params,
    )

