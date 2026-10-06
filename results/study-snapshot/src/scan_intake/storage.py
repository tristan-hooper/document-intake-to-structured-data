"""Atomic page commits and complete-directory publication of reviewable exports."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


class Store:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS sources(sha256 TEXT PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observations(sha256 TEXT REFERENCES sources(sha256),
                filename TEXT NOT NULL, PRIMARY KEY(sha256,filename));
            CREATE TABLE IF NOT EXISTS pages(cache_key TEXT PRIMARY KEY,
                source_sha256 TEXT REFERENCES sources(sha256), page INTEGER NOT NULL,
                pipeline TEXT NOT NULL, status TEXT NOT NULL, body TEXT NOT NULL);
        """)

    def lookup(self,key):
        row = self.connection.execute("SELECT body FROM pages WHERE cache_key=? AND status='completed'",(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def commit_page(self,key,source,pipeline,result):
        body = json.dumps(result,ensure_ascii=False,allow_nan=False)
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO sources VALUES (?,?)",(source["sha256"],source["title"]))
            self.connection.execute("INSERT OR IGNORE INTO observations VALUES (?,?)",(source["sha256"],source["local_file"]))
            self.connection.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?)",
                (key,source["sha256"],result["pdf_page"],pipeline,result["status"],body))

    def observe_alias(self,source):
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO observations VALUES (?,?)",(source["sha256"],source["local_file"]))

    def close(self):
        self.connection.close()


COLUMNS = ["source_id","source_sha256","source_title","pdf_page","printed_page_label",
           "publication_date_or_year","observation_period","target_id","pipeline","configuration_fingerprint",
           "row_label","column_label","period_label","unit_label","context_source","raw_value","value",
           "kind","markers","marker_kind","bounds","confidence_evidence","alignment","disposition","reason","human_confirmation"]


def rows_for_page(result):
    source = result["source"]
    for field in result["regions"]["fields"]:
        row = dict(source_id=source["source_id"],source_sha256=source["sha256"],source_title=source["title"],
            pdf_page=result["pdf_page"],printed_page_label=result["printed_page_label"],
            publication_date_or_year=source["publication_date_or_year"],observation_period=source["observation_period"],
            pipeline=result["pipeline"],configuration_fingerprint=result["configuration_fingerprint"],**field)
        row["confidence_evidence"] = json.dumps([dict(score=u["confidence"],scope=u["confidence_scope"])
                                               for u in field["evidence"]],ensure_ascii=False)
        for key in ("markers","bounds"):
            row[key] = json.dumps(row[key])
        yield {key:row.get(key) for key in COLUMNS}


def export_run(runs,run_id,results,metadata):
    runs = Path(runs)
    runs.mkdir(parents=True,exist_ok=True)
    staging = runs/(".pending-"+uuid4().hex)
    final = runs/run_id
    if final.exists():
        raise FileExistsError("Run identifier already exists")
    staging.mkdir()
    rows = [row for result in results for row in rows_for_page(result)]
    for name,selected in [("candidates.csv",rows),("review.csv",[r for r in rows if r["disposition"] == "review_required"])]:
        with (staging/name).open("w",encoding="utf-8-sig",newline="") as handle:
            writer = csv.DictWriter(handle,fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(selected)
    (staging/"pages.json").write_text(json.dumps(results,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    metadata = {**metadata,"artifact_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in staging.iterdir()}}
    (staging/"run.json").write_text(json.dumps(metadata,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(staging,final)
    pointer = runs/(".current-"+uuid4().hex+".json")
    try:
        pointer.write_text(json.dumps({"run_id":run_id,"complete":True})+"\n",encoding="utf-8")
        os.replace(pointer,runs/"current.json")
    finally:
        pointer.unlink(missing_ok=True)
    return final
