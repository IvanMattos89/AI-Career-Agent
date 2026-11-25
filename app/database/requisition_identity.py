"""Preserve surviving rows and links while changing the identity scheme."""
from app.models.job_listing import JobListing


def migrate_requisition_identity(cursor):
    cursor.execute("ALTER TABLE job_listings ADD COLUMN identity_review INTEGER NOT NULL DEFAULT 0")
    rows = cursor.execute("SELECT * FROM job_listings ORDER BY id").fetchall()
    # Temporary keys avoid transient UNIQUE collisions without merging or deleting history.
    for row in rows:
        cursor.execute("UPDATE job_listings SET canonical_key=? WHERE id=?", (f"migration13:{row['id']}", row["id"]))
    used = set()
    for row in rows:
        key = JobListing(title=row["title"], company=row["company"], location=row["location"],
                         provider=row["provider"], external_id=row["external_id"], url=row["url"],
                         description=row["description"] or "").canonical_key
        if key in used:
            key += f":legacy:{row['id']}"
        used.add(key)
        cursor.execute("UPDATE job_listings SET canonical_key=?, identity_review=1 WHERE id=?", (key, row["id"]))
