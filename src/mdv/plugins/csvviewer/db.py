import sqlite3
import csv
import os

from mdv.logger import get_logger

logger = get_logger(__name__)

_db_cache = {}

def get_csv_db(filepath: str) -> sqlite3.Connection:
    global _db_cache
    
    try:
        stat = os.stat(filepath)
        mtime = stat.st_mtime
        size = stat.st_size
    except OSError:
        raise FileNotFoundError(f"File not found: {filepath}")
    
    cache_key = f"{filepath}_{mtime}_{size}"
    
    if filepath in _db_cache:
        cached_key, conn = _db_cache[filepath]
        if cached_key == cache_key:
            return conn
        else:
            conn.close()
            del _db_cache[filepath]
            
    logger.info(f"Loading CSV into in-memory SQLite: {filepath}")
    conn = load_csv_to_sqlite(filepath)
    _db_cache[filepath] = (cache_key, conn)
    return conn

def convert_val(val: str):
    if not val:
        return None
    try:
        if '.' not in val:
            return int(val)
        return float(val)
    except ValueError:
        return val

def load_csv_to_sqlite(filepath: str) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            raw_headers = next(reader)
        except StopIteration:
            raw_headers = ["col1"]
            
        headers = []
        for i, h in enumerate(raw_headers):
            clean_h = h.strip()
            if not clean_h:
                clean_h = f"col_{i}"
            headers.append(clean_h)
            
        cols_def = ", ".join([f'"{h}"' for h in headers])
        conn.execute(f"CREATE TABLE data ({cols_def})")
        
        placeholders = ", ".join(["?"] * len(headers))
        insert_sql = f"INSERT INTO data VALUES ({placeholders})"
        
        def row_generator():
            for row in reader:
                if len(row) < len(headers):
                    row.extend([""] * (len(headers) - len(row)))
                elif len(row) > len(headers):
                    row = row[:len(headers)]
                    
                yield [convert_val(x) for x in row]
                
        conn.executemany(insert_sql, row_generator())
        
    conn.row_factory = sqlite3.Row
    return conn
