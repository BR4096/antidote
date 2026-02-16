"""SQLite FTS5 memory store for Antidote.

Provides persistent, full-text-searchable memory using SQLite with FTS5
virtual tables. Supports async access via aiosqlite with WAL mode for
concurrent reads during writes.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiosqlite


# --- Interface (from contracts) ---

@dataclass
class MemoryEntry:
    id: int
    content: str
    category: str       # "fact", "conversation", "solution", "preference"
    created_at: str
    relevance: float    # Search relevance score (0-1)


class BaseMemory(ABC):
    @abstractmethod
    async def save(self, content: str, category: str = "fact") -> int:
        """Store a memory. Returns the ID."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memories by keyword. Returns ranked results."""
        ...

    @abstractmethod
    async def forget(self, memory_id: int) -> bool:
        """Delete a specific memory."""
        ...

    @abstractmethod
    async def recent(self, limit: int = 20) -> list[MemoryEntry]:
        """Get most recent memories."""
        ...


# --- Schema ---

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'fact',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    category,
    content='memories',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, category) VALUES (new.id, new.content, new.category);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, category) VALUES ('delete', old.id, old.content, old.category);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, category) VALUES ('delete', old.id, old.content, old.category);
    INSERT INTO memories_fts(rowid, content, category) VALUES (new.id, new.content, new.category);
END;
"""


def _word_overlap(a: str, b: str) -> float:
    """Return the fraction of shared words between two strings (0-1)."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller


class MemoryStore(BaseMemory):
    """SQLite FTS5 memory store with async access.

    Usage:
        store = MemoryStore("~/.antidote/memory.db")
        await store.initialize()
        mem_id = await store.save("Mark prefers dark mode", "preference")
        results = await store.search("dark mode")
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = os.path.expanduser(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database and create tables if needed."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            await self.initialize()
        assert self._db is not None
        return self._db

    async def save(self, content: str, category: str = "fact") -> int:
        """Store a memory with auto-deduplication.

        If content has >80% word overlap with an existing entry in the same
        category, the existing entry is updated instead of creating a new one.
        Returns the memory ID.
        """
        db = await self._ensure_db()

        # Check for duplicates: search existing memories in same category
        async with db.execute(
            "SELECT id, content FROM memories WHERE category = ?",
            (category,),
        ) as cursor:
            async for row in cursor:
                if _word_overlap(content, row[1]) > 0.8:
                    # Update existing entry
                    await db.execute(
                        "UPDATE memories SET content = ?, updated_at = datetime('now') WHERE id = ?",
                        (content, row[0]),
                    )
                    await db.commit()
                    return row[0]

        # No duplicate found — insert new
        async with db.execute(
            "INSERT INTO memories (content, category) VALUES (?, ?)",
            (content, category),
        ) as cursor:
            mem_id = cursor.lastrowid
        await db.commit()
        return mem_id  # type: ignore[return-value]

    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memories using FTS5 MATCH with bm25() ranking.

        Returns results ordered by relevance (best match first).
        """
        db = await self._ensure_db()

        # Escape FTS5 special characters and build query
        safe_query = query.replace('"', '""')
        fts_query = f'"{safe_query}"'

        results: list[MemoryEntry] = []
        try:
            async with db.execute(
                """
                SELECT m.id, m.content, m.category, m.created_at, bm25(memories_fts) AS rank
                FROM memories_fts
                JOIN memories m ON m.id = memories_fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            ) as cursor:
                async for row in cursor:
                    # bm25() returns negative values (more negative = more relevant)
                    # Normalize to 0-1 scale where 1 = most relevant
                    raw_rank = row[4]
                    relevance = min(1.0, max(0.0, -raw_rank))
                    results.append(
                        MemoryEntry(
                            id=row[0],
                            content=row[1],
                            category=row[2],
                            created_at=row[3],
                            relevance=relevance,
                        )
                    )
        except aiosqlite.OperationalError:
            # No matches or FTS table issue — return empty
            pass

        return results

    async def forget(self, memory_id: int) -> bool:
        """Delete a specific memory by ID. Returns True if deleted."""
        db = await self._ensure_db()
        async with db.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            deleted = cursor.rowcount > 0
        await db.commit()
        return deleted

    async def recent(self, limit: int = 20) -> list[MemoryEntry]:
        """Get the most recently created/updated memories."""
        db = await self._ensure_db()
        results: list[MemoryEntry] = []
        async with db.execute(
            """
            SELECT id, content, category, created_at
            FROM memories
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            async for row in cursor:
                results.append(
                    MemoryEntry(
                        id=row[0],
                        content=row[1],
                        category=row[2],
                        created_at=row[3],
                        relevance=0.0,
                    )
                )
        return results

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
