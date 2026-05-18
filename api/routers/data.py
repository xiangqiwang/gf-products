# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/data.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/data", tags=["data"])

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_file_info(file_path: Path) -> dict:
    """Get file information"""
    stat = file_path.stat()
    record_count = None

    # Try to get record count
    try:
        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    record_count = len(data)
        elif file_path.suffix == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for _ in f) - 1  # Subtract header row
    except Exception:
        pass

    return {
        "name": file_path.name,
        "path": str(file_path.relative_to(DATA_DIR)),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "record_count": record_count,
        "type": file_path.suffix[1:] if file_path.suffix else "unknown"
    }


@router.get("/files")
async def list_data_files(platform: Optional[str] = None, file_type: Optional[str] = None):
    """Get data file list"""
    if not DATA_DIR.exists():
        return {"files": []}

    files = []
    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            # Platform filter
            if platform:
                rel_path = str(file_path.relative_to(DATA_DIR))
                if platform.lower() not in rel_path.lower():
                    continue

            # Type filter
            if file_type and file_path.suffix[1:].lower() != file_type.lower():
                continue

            try:
                files.append(get_file_info(file_path))
            except Exception:
                continue

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x["modified_at"], reverse=True)

    return {"files": files}


@router.get("/files/{file_path:path}")
async def get_file_content(file_path: str, preview: bool = True, limit: int = 100):
    """Get file content or preview"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check: ensure within DATA_DIR
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if preview:
        # Return preview data
        try:
            if full_path.suffix == ".json":
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"data": data[:limit], "total": len(data)}
                    return {"data": data, "total": 1}
            elif full_path.suffix == ".csv":
                import csv
                with open(full_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= limit:
                            break
                        rows.append(row)
                    # Re-read to get total count
                    f.seek(0)
                    total = sum(1 for _ in f) - 1
                    return {"data": rows, "total": total}
            elif full_path.suffix.lower() in (".xlsx", ".xls"):
                import pandas as pd
                # Read first limit rows
                df = pd.read_excel(full_path, nrows=limit)
                # Get total row count (only read first column to save memory)
                df_count = pd.read_excel(full_path, usecols=[0])
                total = len(df_count)
                # Convert to list of dictionaries, handle NaN values
                rows = df.where(pd.notnull(df), None).to_dict(orient='records')
                return {
                    "data": rows,
                    "total": total,
                    "columns": list(df.columns)
                }
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type for preview")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Return file download
        return FileResponse(
            path=full_path,
            filename=full_path.name,
            media_type="application/octet-stream"
        )


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download file"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="application/octet-stream"
    )


@router.get("/stats")
async def get_data_stats():
    """Get data statistics"""
    if not DATA_DIR.exists():
        return {"total_files": 0, "total_size": 0, "by_platform": {}, "by_type": {}}

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_platform": {},
        "by_type": {}
    }

    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                stat = file_path.stat()
                stats["total_files"] += 1
                stats["total_size"] += stat.st_size

                # Statistics by type
                file_type = file_path.suffix[1:].lower()
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1

                # Statistics by platform (inferred from path)
                rel_path = str(file_path.relative_to(DATA_DIR))
                for platform in ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]:
                    if platform in rel_path.lower():
                        stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
                        break
            except Exception:
                continue

    return stats

@router.get("/sqlite_query")
async def sqlite_query(
    platform: str = "all", 
    keyword: str = None, 
    start_time: int = None, 
    end_time: int = None, 
    limit: int = 50, 
    page: int = 1
):
    """Query data from SQLite with standardized columns and pagination"""
    db_path = Path("database/sqlite_tables.db")
    if not db_path.exists():
        return {"data": [], "total": 0, "error": "Database not found"}

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    if start_time is None:
        start_time = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
    if end_time is None:
        end_time = int(datetime.now().timestamp() * 1000)

    offset = (page - 1) * limit
    
    # 1. Identify valid platforms
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    full_platform_map = {
        "xhs": ("xhs_note", "time", ["title", "desc", "source_keyword"], "xhs_creator", "user_id", "user_id", {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
        "dy": ("douyin_aweme", "create_time", ["title", "desc", "source_keyword"], "dy_creator", "user_id", "user_id", {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
        "ks": ("kuaishou_video", "create_time", ["title", "desc", "source_keyword"], None, None, None, {}),
        "bili": ("bilibili_video", "create_time", ["title", "desc", "source_keyword"], "bilibili_up_info", "user_id", "user_id", {"gender":"sex", "fans":"total_fans", "ip":None}),
        "wb": ("weibo_note", "create_time", ["content", "source_keyword"], "weibo_creator", "user_id", "user_id", {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
        "tieba": ("tieba_note", "publish_time", ["title", "desc", "source_keyword"], "tieba_creator", "user_nickname", "nickname", {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
        "zhihu": ("zhihu_content", "created_time", ["title", "desc", "source_keyword"], "zhihu_creator", "user_id", "user_id", {"gender":"gender", "fans":"fans", "ip":"ip_location"})
    }
    
    requested_platforms = platform.split(",")
    if "all" in requested_platforms or "mixed" in requested_platforms:
        all_p = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
        platforms_to_query = [p for p in all_p if full_platform_map[p][0] in existing_tables]
    else:
        platforms_to_query = [p for p in requested_platforms if p in full_platform_map and full_platform_map[p][0] in existing_tables]
        
    if not platforms_to_query:
        conn.close()
        return {"data": [], "total": 0}

    # 2. Build sub-queries
    all_queries = []
    all_params = []
    total_count = 0
    
    for p in platforms_to_query:
        table_info = full_platform_map[p]
        table_name, time_field, search_fields, creator_table, main_key, creator_key, field_map = table_info
        
        # Timestamp normalization
        s_start, s_end = start_time, end_time
        if s_start and s_start > 1000000000000 and p != "xhs": s_start = int(s_start / 1000)
        if s_end and s_end > 1000000000000 and p != "xhs": s_end = int(s_end / 1000)
        
        conditions = " WHERE 1=1"
        sub_params = []
        if keyword:
            like_clauses = " OR ".join([f"m.{f} LIKE ?" for f in search_fields])
            conditions += f" AND ({like_clauses})"
            sub_params.extend([f"%{keyword}%" for _ in search_fields])
        if s_start:
            conditions += f" AND m.{time_field} >= ?"
            sub_params.append(s_start)
        if s_end:
            actual_end = s_end + 86400 if p == "wb" else s_end
            conditions += f" AND m.{time_field} <= ?"
            sub_params.append(actual_end)
            
        # Get count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} m" + conditions, sub_params)
        total_count += cursor.fetchone()[0]
        
        # Define creator fields
        if p == "wb":
            g_col, f_col, i_col = "m.gender", "m.user_fans_count", "m.ip_location"
            creator_join = ""
        elif creator_table:
            g_col = f"c.{field_map['gender']}" if field_map.get('gender') else "NULL"
            f_col = f"c.{field_map['fans']}" if field_map.get('fans') else "NULL"
            i_col = f"c.{field_map['ip']}" if field_map.get('ip') else "NULL"
            creator_join = f"LEFT JOIN {creator_table} c ON m.{main_key} = c.{creator_key}"
        else:
            g_col, f_col, i_col = "NULL", "NULL", "NULL"
            creator_join = ""

        # Standard columns (13 base)
        if p == "xhs":
            std = "CAST(m.note_id AS TEXT) as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.time as create_time, m.liked_count, m.comment_count as comments_count, m.share_count as shared_count, m.note_url, m.ip_location"
        elif p == "wb":
            std = "CAST(m.note_id AS TEXT) as note_id, m.user_id, m.nickname, m.avatar, '' as title, '' as desc, m.content, m.create_time * 1000 as create_time, m.liked_count, m.comments_count, m.shared_count, m.note_url, m.ip_location"
        elif p == "dy":
            std = "CAST(m.aweme_id AS TEXT) as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time * 1000 as create_time, m.liked_count, m.comment_count as comments_count, m.share_count as shared_count, m.aweme_url as note_url, m.ip_location"
        elif p == "bili":
            std = "CAST(m.video_id AS TEXT) as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time * 1000 as create_time, m.liked_count, m.video_comment as comments_count, m.video_share_count as shared_count, m.video_url as note_url, '' as ip_location"
        elif p == "tieba":
            std = "CAST(m.id AS TEXT) as note_id, '' as user_id, m.user_nickname as nickname, '' as avatar, m.title, m.desc, '' as content, m.publish_time as create_time, '0' as liked_count, m.total_replay_num as comments_count, '0' as shared_count, m.note_url, m.ip_location"
        elif p == "zhihu":
            std = "CAST(m.id AS TEXT) as note_id, m.user_id, m.user_nickname as nickname, m.user_avatar as avatar, m.title, m.desc, m.content_text as content, m.created_time as create_time, m.voteup_count as liked_count, m.comment_count as comments_count, '0' as shared_count, m.content_url as note_url, '' as ip_location"
        else: # ks or others (Kuaishou doesn't have ip_location in its note table)
            std = "CAST(m.id AS TEXT) as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time * 1000 as create_time, m.liked_count, '0' as comments_count, '0' as shared_count, m.video_url as note_url, '' as ip_location"

        sub_q = f"SELECT {std}, '{p}' as platform_type, m.last_modify_ts, {g_col} as c_gender, {f_col} as c_fans, {i_col} as c_ip FROM {table_name} m {creator_join} {conditions}"
        all_queries.append(sub_q)
        all_params.extend(sub_params)
        
    # 3. Final execution with total count and sorting
    final_query = f"SELECT * FROM ({' UNION ALL '.join(all_queries)}) AS combined ORDER BY create_time DESC LIMIT ? OFFSET ?"
    count_query = f"SELECT COUNT(*) FROM ({' UNION ALL '.join(all_queries)}) AS combined"
    
    try:
        # Get total count for pagination
        cursor.execute(count_query, all_params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated and sorted results
        cursor.execute(final_query, all_params + [limit, offset])
        rows = cursor.fetchall()
        
        all_results = []
        for row in rows:
            item = dict(row)
            # Normalize display fields
            gender = str(item.get('c_gender') or '0')
            if gender in ('1', 'm'):
                item['display_gender'] = '男'
            elif gender in ('2', 'f'):
                item['display_gender'] = '女'
            else:
                item['display_gender'] = '-'
            
            item['display_fans'] = item.get('c_fans') or '-'
            item['display_ip'] = item.get('c_ip') or item.get('ip_location') or '-'
            all_results.append(item)
            
        conn.close()
        return {
            "data": all_results,
            "total": total_count,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        if 'conn' in locals(): conn.close()
        import traceback
        return {"data": [], "total": 0, "error": str(e), "trace": traceback.format_exc()}


@router.post("/clear_database")
async def clear_database():
    """Clear all data by dropping and recreating tables"""
    from database.db_session import create_tables, delete_all_tables
    from ..services.crawler_manager import crawler_manager
    
    try:
        await crawler_manager.add_system_log("Attempting to clear database and re-initialize tables...", "warning")
        
        # 1. Drop all tables (safe even if file is 'locked' by current process pool)
        await delete_all_tables()
        
        # 2. Re-initialize tables
        await create_tables()
        
        await crawler_manager.add_system_log("Database cleared and re-initialized successfully.", "success")
        return {"message": "Database cleared and re-initialized successfully"}
    except Exception as e:
        import traceback
        err_msg = f"Failed to clear database: {str(e)}"
        await crawler_manager.add_system_log(err_msg, "error")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=err_msg)


@router.get("/collection_history")
async def get_collection_history(limit: int = 20):
    """Get collection task history from SQLite"""
    db_path = DATA_DIR.parent / "database" / "sqlite_tables.db"
    if not db_path.exists():
        return {"data": []}
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_log'")
        if not cursor.fetchone():
            conn.close()
            return {"data": []}
            
        cursor.execute("SELECT * FROM collection_log ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        conn.close()
        return {"data": data}
    except Exception as e:
        return {"data": [], "error": str(e)}
@router.get("/task_results/{task_id}")
async def get_task_results(task_id: int):
    """Get collected items for a specific task by matching time range and platform"""
    db_path = DATA_DIR.parent / "database" / "sqlite_tables.db"
    if not db_path.exists():
        return {"data": []}
    
    try:
        import sqlite3
        import time
        from datetime import datetime
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Get task info
        cursor.execute("SELECT platform, start_time, end_time FROM collection_log WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            conn.close()
            return {"data": [], "error": "Task not found"}
            
        platform = task['platform']
        # Convert start/end time string to timestamp (ms)
        # Using last_modify_ts as it updates on every crawl, add_ts only on first seen
        start_ts = int(time.mktime(time.strptime(task['start_time'], "%Y-%m-%d %H:%M:%S"))) * 1000 - 2000
        end_time_str = task['end_time'] or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_ts = int(time.mktime(time.strptime(end_time_str, "%Y-%m-%d %H:%M:%S"))) * 1000 + 5000 # Add buffer
        
        # 2. Query platform table with creator info fallback
        table_map = {
            'xhs': ('xhs_note', 'xhs_creator', 'user_id', 'user_id', {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
            'dy': ('douyin_aweme', 'dy_creator', 'user_id', 'user_id', {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
            'bili': ('bilibili_video', 'bilibili_up_info', 'user_id', 'user_id', {"gender":"sex", "fans":"total_fans", "ip":None}),
            'wb': ('weibo_note', 'weibo_creator', 'user_id', 'user_id', {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
            'ks': ('kuaishou_video', None, None, None, {}),
            'zhihu': ('zhihu_content', 'zhihu_creator', 'user_id', 'user_id', {"gender":"gender", "fans":"fans", "ip":"ip_location"}),
            'tieba': ('tieba_note', 'tieba_creator', 'user_nickname', 'nickname', {"gender":"gender", "fans":"fans", "ip":"ip_location"})
        }
        
        mapping = table_map.get(platform)
        if not mapping:
            conn.close()
            return {"data": [], "error": f"Platform {platform} results mapping not supported"}
            
        main_table, creator_table, main_key, creator_key, field_map = mapping
        
        # Build query to include fallback fields
        # Build query to include fallback fields with explicit column names to avoid ambiguity
        if platform == "xhs":
            std_cols = "m.note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.time as create_time, m.liked_count, m.comment_count as comments_count, m.share_count as shared_count, m.note_url, m.ip_location, m.last_modify_ts"
        elif platform == "wb":
            std_cols = "m.note_id, m.user_id, m.nickname, m.avatar, '' as title, '' as desc, m.content, m.create_time, m.liked_count, m.comments_count, m.shared_count, m.note_url, m.ip_location, m.last_modify_ts"
        elif platform == "dy":
            std_cols = "m.aweme_id as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time, m.liked_count, m.comment_count as comments_count, m.share_count as shared_count, m.aweme_url as note_url, m.ip_location, m.last_modify_ts"
        elif platform == "bili":
            std_cols = "m.video_id as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time, m.liked_count, '0' as comments_count, m.video_share_count as shared_count, m.video_url as note_url, '' as ip_location, m.last_modify_ts"
        elif platform == "tieba":
            std_cols = "m.id as note_id, '' as user_id, m.user_nickname as nickname, '' as avatar, m.title, m.desc, '' as content, m.publish_time as create_time, '0' as liked_count, '0' as comments_count, '0' as shared_count, m.note_url, '' as ip_location, m.last_modify_ts"
        elif platform == "zhihu":
            std_cols = "m.id as note_id, m.user_id, m.user_nickname as nickname, m.user_avatar as avatar, m.title, m.desc, m.content_text as content, m.created_time as create_time, m.voteup_count as liked_count, m.comment_count as comments_count, '0' as shared_count, m.content_url as note_url, '' as ip_location, m.last_modify_ts"
        else:
            std_cols = "m.id as note_id, m.user_id, m.nickname, m.avatar, m.title, m.desc, '' as content, m.create_time, m.liked_count, '0' as comments_count, '0' as shared_count, '' as note_url, '' as ip_location, m.last_modify_ts"

        if creator_table and main_key and creator_key:
            g_col = f"c.{field_map['gender']}" if field_map.get('gender') else "NULL"
            f_col = f"c.{field_map['fans']}" if field_map.get('fans') else "NULL"
            i_col = f"c.{field_map['ip']}" if field_map.get('ip') else "NULL"
            
            query = f"""
                SELECT {std_cols}, 
                       {g_col} as c_gender, 
                       {f_col} as c_fans, 
                       {i_col} as c_ip
                FROM {main_table} m
                LEFT JOIN {creator_table} c ON m.{main_key} = c.{creator_key}
                WHERE m.last_modify_ts >= ? AND m.last_modify_ts <= ?
                ORDER BY m.last_modify_ts DESC
            """
        else:
            query = f"SELECT {std_cols}, NULL as c_gender, NULL as c_fans, NULL as c_ip FROM {main_table} m WHERE m.last_modify_ts >= ? AND m.last_modify_ts <= ? ORDER BY m.last_modify_ts DESC"
            
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()
        
        # 3. Map to unified result format
        results = []
        for i, row in enumerate(rows):
            row_dict = dict(row)
            
            # Extract common fields
            content = row_dict.get('title') or row_dict.get('desc') or row_dict.get('content') or row_dict.get('content_text') or '-'
            if len(content) > 50: content = content[:50] + '...'
            
            nickname = row_dict.get('nickname') or row_dict.get('user_nickname') or row_dict.get('user_name') or '-'
            
            # Interaction data
            likes = row_dict.get('liked_count') or row_dict.get('voteup_count') or '0'
            comments = row_dict.get('comment_count') or row_dict.get('comments_count') or row_dict.get('video_comment') or '0'
            
            # --- New Fields: Gender, Fans, IP ---
            # 1. Gender
            gender = row_dict.get('gender') or row_dict.get('c_gender') or '-'
            if gender == '1': gender = '男'
            elif gender == '2': gender = '女'
            elif not gender or gender == '0': gender = '-'
            
            # 2. Fans
            fans = row_dict.get('user_fans_count') or row_dict.get('c_fans') or row_dict.get('fans') or '-'
            
            # 3. IP
            ip = row_dict.get('ip_location') or row_dict.get('c_ip') or '-'
            
            link = row_dict.get('note_url') or row_dict.get('aweme_url') or row_dict.get('video_url') or row_dict.get('content_url') or '#'
            
            results.append({
                "index": i + 1,
                "content": content,
                "nickname": nickname,
                "gender": gender,
                "fans": fans,
                "ip": ip,
                "stats": f"👍{likes} 💬{comments}",
                "link": link
            })
            
        conn.close()
        return {"data": results}
    except Exception as e:
        return {"data": [], "error": str(e)}

@router.get("/task_logs/{task_id}")
async def get_task_full_logs(task_id: int):
    """Get full log file content for a specific task"""
    db_path = DATA_DIR.parent / "database" / "sqlite_tables.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT log_file_path FROM collection_log WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row['log_file_path']:
            raise HTTPException(status_code=404, detail="Log file path not found for this task")
            
        log_path = DATA_DIR.parent / row['log_file_path']
        if not log_path.exists():
            # Try absolute path if relative fails
            if os.path.isabs(row['log_file_path']) and os.path.exists(row['log_file_path']):
                log_path = Path(row['log_file_path'])
            else:
                raise HTTPException(status_code=404, detail=f"Log file not found at {log_path}")
        
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
