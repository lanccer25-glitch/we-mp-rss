from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import sqlite3
import requests
import re
import time
from datetime import datetime
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from core.config import cfg
from core.print import print_info, print_success, print_error

router = APIRouter(prefix="/api/v1/notion", tags=["notion"])

sync_status = {"running": False, "last_run": None, "last_result": None, "success": 0, "failed": 0, "total": 0}

def get_db_path():
    db_url = cfg.get("db", "sqlite:///data/db.db")
    return db_url.replace("sqlite:///", "")

def get_unsynced_articles(db_path, batch_size=50):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.title, a.url, a.description,
               a.content, a.pic_url, a.publish_time, a.status,
               f.mp_name
        FROM articles a
        LEFT JOIN feeds f ON a.mp_id = f.id
        WHERE a.content IS NOT NULL AND a.content != ""
          AND a.status = 1
          AND (a.is_export IS NULL OR a.is_export = 0)
        ORDER BY a.publish_time DESC
        LIMIT ?
    """, (batch_size,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def mark_exported(db_path, article_id):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE articles SET is_export = 1 WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

def html_to_blocks(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script","style"]):
        t.decompose()
    text = md(str(soup), heading_style="ATX", bullets="-")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    blocks = []
    for line in text.split("\n"):
        if len(blocks) >= 100:
            break
        if line.startswith("### "):
            blocks.append({"object":"block","type":"heading_3","heading_3":{"rich_text":[{"type":"text","text":{"content":line[4:].strip()[:2000]}}]}})
        elif line.startswith("## "):
            blocks.append({"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":line[3:].strip()[:2000]}}]}})
        elif line.startswith("# "):
            blocks.append({"object":"block","type":"heading_1","heading_1":{"rich_text":[{"type":"text","text":{"content":line[2:].strip()[:2000]}}]}})
        elif line.strip():
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":line.strip()[:2000]}}]}})
    return blocks

def do_sync():
    global sync_status
    sync_status["running"] = True
    sync_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sync_status["success"] = 0
    sync_status["failed"] = 0

    token = cfg.get("notion.token", "")
    database_id = cfg.get("notion.database_id", "")
    batch_size = int(cfg.get("notion.batch_size", 50))

    if not token or not database_id:
        sync_status["last_result"] = "error: notion.token or notion.database_id not configured"
        sync_status["running"] = False
        return

    db_path = get_db_path()
    articles = get_unsynced_articles(db_path, batch_size)
    sync_status["total"] = len(articles)

    if not articles:
        sync_status["last_result"] = "no new articles"
        sync_status["running"] = False
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    for a in articles:
        try:
            pub_date = None
            if a.get("publish_time"):
                pub_date = datetime.fromtimestamp(a["publish_time"]).isoformat()
            props = {
                "文章标题": {"title": [{"text": {"content": (a.get("title") or "untitled")[:200]}}]},
                "公众号": {"select": {"name": a.get("mp_name") or "unknown"}},
                "文章链接": {"url": a.get("url")},
            }
            if pub_date:
                props["发布时间"] = {"date": {"start": pub_date}}
            if a.get("description"):
                props["摘要"] = {"rich_text": [{"text": {"content": a["description"][:2000]}}]}
            children = html_to_blocks(a.get("content") or "")
            payload = {"parent": {"database_id": database_id}, "properties": props, "children": children}
            resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            mark_exported(db_path, a["id"])
            sync_status["success"] += 1
            print_success(f"Notion sync: {(a.get('title') or '')[:30]}")
        except Exception as e:
            sync_status["failed"] += 1
            print_error(f"Notion sync failed: {(a.get('title') or '')[:30]} - {e}")

    sync_status["last_result"] = f"done: {sync_status['success']} ok, {sync_status['failed']} fail, {sync_status['total']} total"
    sync_status["running"] = False

@router.post("/sync")
async def trigger_sync(bg: BackgroundTasks):
    if sync_status["running"]:
        return {"status": "busy", "message": "sync in progress"}
    bg.add_task(do_sync)
    return {"status": "started"}

@router.get("/sync/status")
async def get_status():
    return sync_status
