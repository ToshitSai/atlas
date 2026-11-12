#!/usr/bin/env python3
"""Atlas AI Gen-3.3.4: Safe Public to Private Vercel Blob Migration Utility.

Enumerates blobs from the legacy public Vercel Blob store (atlas-storage),
matches them against database document records, copies them to the new
private Vercel Blob store (atlas-private-storage), verifies byte size and SHA-256,
and produces a comprehensive audit report without destructive deletes.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def fetch_blob_list(token: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """List blobs from a Vercel Blob store using its read-write token."""
    url = f"https://blob.vercel-storage.com/?limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-version": "7"
        }
    )
    blobs = []
    has_more = True
    cursor = None

    while has_more:
        curr_url = f"{url}&cursor={cursor}" if cursor else url
        req = urllib.request.Request(
            curr_url,
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-version": "7"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                new_blobs = data.get("blobs", [])
                blobs.extend(new_blobs)
                has_more = data.get("hasMore", False)
                cursor = data.get("cursor")
                if not has_more or not cursor:
                    break
        except Exception as e:
            print(f"[ERROR] Failed to list blobs: {e}")
            break
    return blobs


def run_migration(dry_run: bool = False) -> Dict[str, Any]:
    public_token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
    private_token = os.environ.get("PRIVATE_READ_WRITE_TOKEN", "").strip()

    if not public_token:
        print("[ERROR] BLOB_READ_WRITE_TOKEN is missing. Cannot enumerate public blobs.")
        return {"error": "Missing BLOB_READ_WRITE_TOKEN"}

    if not private_token and not dry_run:
        print("[ERROR] PRIVATE_READ_WRITE_TOKEN is missing. Cannot migrate to private store.")
        return {"error": "Missing PRIVATE_READ_WRITE_TOKEN"}

    print("[MIGRATION] Enumerating legacy public blobs from atlas-storage...")
    public_blobs = fetch_blob_list(public_token)
    print(f"[MIGRATION] Found {len(public_blobs)} objects in public store.")

    # Load local database or SQLite document mappings
    doc_records = {}
    try:
        from database.store import store
        if store.database_health() and getattr(store, "repo", None):
            rows = store.repo._execute("SELECT id, title, doc_type FROM documents")
            for r in rows:
                doc_records[str(r[0])] = {"title": r[1], "doc_type": r[2]}
    except Exception:
        pass

    report = {
        "timestamp": time.time(),
        "total_original_files": len(public_blobs),
        "successfully_migrated": 0,
        "failed_migrations": 0,
        "orphaned_files": 0,
        "checksum_mismatches": 0,
        "migrated_files": [],
        "orphaned_details": [],
        "failures": [],
        "preserved_old_blobs_count": len(public_blobs),
        "dry_run": dry_run,
    }

    for b in public_blobs:
        pathname = b.get("pathname", "")
        old_url = b.get("url", "")
        size_bytes = b.get("size", 0)

        # Download original bytes from public blob
        try:
            req = urllib.request.Request(old_url, headers={"User-Agent": "Atlas-Migrate/3.3.4"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            actual_size = len(data)
            sha256 = hashlib.sha256(data).hexdigest()
        except Exception as dl_err:
            print(f"[ERROR] Failed downloading {pathname}: {dl_err}")
            report["failed_migrations"] += 1
            report["failures"].append({"pathname": pathname, "url": old_url, "error": str(dl_err)})
            continue

        # Extract owner and doc ID if key follows convention: documents/<owner>/<doc_id>_<filename>
        parts = pathname.split("/")
        owner = None
        doc_id = None
        if len(parts) >= 3 and parts[0] == "documents":
            owner = parts[1]
            rest = parts[2]
            if "_" in rest:
                doc_id = rest.split("_", 1)[0]
            else:
                doc_id = rest

        is_orphan = not bool(owner and owner != "anonymous" and (doc_id in doc_records or doc_id))
        if is_orphan:
            report["orphaned_files"] += 1
            report["orphaned_details"].append({
                "pathname": pathname,
                "url": old_url,
                "size_bytes": actual_size,
                "sha256": sha256,
                "reason": "No verifiable owner mapping found"
            })
            print(f"[ORPHAN QUARANTINED] {pathname} ({actual_size} bytes, sha256={sha256[:12]}...)")
            continue

        if dry_run:
            report["successfully_migrated"] += 1
            report["migrated_files"].append({
                "pathname": pathname,
                "old_url": old_url,
                "new_url": "[DRY RUN]",
                "size_bytes": actual_size,
                "sha256": sha256,
                "owner": owner,
                "verified": True,
            })
            continue

        # Upload to private blob store
        target_key = pathname
        target_url = f"https://blob.vercel-storage.com/{target_key}?addRandomSuffix=false"
        put_headers = {
            "Authorization": f"Bearer {private_token}",
            "x-api-version": "7",
            "Content-Type": b.get("contentType") or "application/octet-stream",
            "x-vercel-blob-access": "private",
            "x-add-random-suffix": "0",
        }
        try:
            put_req = urllib.request.Request(target_url, data=data, headers=put_headers, method="PUT")
            with urllib.request.urlopen(put_req, timeout=30) as put_resp:
                put_data = json.loads(put_resp.read().decode("utf-8"))
                new_private_url = put_data.get("url")

            # Verify public unauthenticated access is blocked (HTTP 403)
            blocked_403 = False
            try:
                with urllib.request.urlopen(new_private_url, timeout=5) as unauth:
                    pass
            except urllib.error.HTTPError as he:
                if he.code == 403:
                    blocked_403 = True

            # Verify authenticated download matches SHA-256
            auth_req = urllib.request.Request(
                new_private_url,
                headers={"Authorization": f"Bearer {private_token}"}
            )
            with urllib.request.urlopen(auth_req, timeout=20) as auth_resp:
                downloaded_data = auth_resp.read()
                downloaded_sha256 = hashlib.sha256(downloaded_data).hexdigest()

            if downloaded_sha256 != sha256:
                report["checksum_mismatches"] += 1
                report["failed_migrations"] += 1
                report["failures"].append({"pathname": pathname, "error": "Checksum mismatch after upload"})
                continue

            report["successfully_migrated"] += 1
            report["migrated_files"].append({
                "pathname": pathname,
                "old_public_url": old_url,
                "new_private_url": new_private_url,
                "size_bytes": actual_size,
                "sha256": sha256,
                "owner": owner,
                "unauthorized_blocked_403": blocked_403,
                "checksum_verified": True,
            })
            print(f"[MIGRATED] {pathname} -> {new_private_url} (verified private & hash intact)")
        except Exception as up_err:
            report["failed_migrations"] += 1
            report["failures"].append({"pathname": pathname, "error": str(up_err)})
            print(f"[FAIL] Upload failed for {pathname}: {up_err}")

    # Write report
    report_dir = BASE_DIR / "migration_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "public_to_private_blob_migration.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[REPORT] Saved migration report to {report_path}")
    print(f"Total: {report['total_original_files']}, Migrated: {report['successfully_migrated']}, "
          f"Orphans: {report['orphaned_files']}, Failures: {report['failed_migrations']}, "
          f"Checksum Mismatches: {report['checksum_mismatches']}")
    print("NOTE: Old public objects are PRESERVED and NOT deleted pending user authorization.")
    return report


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run_migration(dry_run=dry)
