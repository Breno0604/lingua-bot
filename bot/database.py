"""
LinguaBot --- Database Abstraction Layer

Suporta dois modos:
  - SQLiteDatabase (dev local, sem configuracao)
  - SupabaseDatabase (producao no Render, usando supabase-py)

A escolha e feita automaticamente baseada na presenca de SUPABASE_URL.
"""

from __future__ import annotations

import sqlite3
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VocabEntry:
    """Uma palavra aprendida pelo usuario."""
    id: int
    user_id: int
    word: str
    translation: str
    context: Optional[str]
    created_at: str
    reviewed_at: Optional[str]
    practice_count: int


class BaseDatabase(ABC):
    """Interface abstrata para operacoes de banco de dados."""

    @abstractmethod
    async def save_vocab(
        self, user_id: int, word: str, translation: str, context: str
    ) -> None:
        """Salva uma nova palavra no vocabulario do usuario."""
        ...

    @abstractmethod
    async def get_vocab(
        self, user_id: int, page: int = 1, page_size: int = 10
    ) -> list[VocabEntry]:
        """Retorna o vocabulario do usuario com paginacao."""
        ...

    @abstractmethod
    async def get_vocab_count(self, user_id: int) -> int:
        """Retorna o total de palavras aprendidas pelo usuario."""
        ...

    @abstractmethod
    async def practice_word(self, user_id: int, word_id: int) -> None:
        """Incrementa o contador de pratica de uma palavra."""
        ...


class SQLiteDatabase(BaseDatabase):
    """Implementacao local com SQLite (para desenvolvimento)."""

    def __init__(self, db_path: str = "bot/data/vocabulary.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    practice_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, word)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    async def save_vocab(
        self, user_id: int, word: str, translation: str, context: str
    ) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO vocabulary (user_id, word, translation, context)
                   VALUES (?, ?, ?, ?)""",
                (user_id, word.lower().strip(), translation.strip(), context),
            )
            conn.commit()
        finally:
            conn.close()

    async def get_vocab(
        self, user_id: int, page: int = 1, page_size: int = 10
    ) -> list[VocabEntry]:
        offset = (page - 1) * page_size
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM vocabulary
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (user_id, page_size, offset),
            ).fetchall()
            return [
                VocabEntry(
                    id=row["id"],
                    user_id=row["user_id"],
                    word=row["word"],
                    translation=row["translation"],
                    context=row["context"],
                    created_at=row["created_at"],
                    reviewed_at=row["reviewed_at"],
                    practice_count=row["practice_count"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    async def get_vocab_count(self, user_id: int) -> int:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as total FROM vocabulary WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row["total"]
        finally:
            conn.close()

    async def practice_word(self, user_id: int, word_id: int) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """UPDATE vocabulary
                   SET practice_count = practice_count + 1,
                       reviewed_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND user_id = ?""",
                (word_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


class SupabaseDatabase(BaseDatabase):
    """Implementacao para producao com Supabase (PostgreSQL)."""

    def __init__(self, supabase_url: str, supabase_key: str):
        from supabase import create_client

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL e SUPABASE_KEY sao obrigatorios para modo Supabase"
            )
        self._client = create_client(supabase_url, supabase_key)

    async def save_vocab(
        self, user_id: int, word: str, translation: str, context: str
    ) -> None:
        data = {
            "user_id": user_id,
            "word": word.lower().strip(),
            "translation": translation.strip(),
            "context": context,
        }
        # Usa upsert para evitar duplicatas (UNIQUE constraint em user_id + word)
        self._client.table("vocabulary").upsert(
            data, on_conflict=["user_id", "word"]
        ).execute()

    async def get_vocab(
        self, user_id: int, page: int = 1, page_size: int = 10
    ) -> list[VocabEntry]:
        offset = (page - 1) * page_size
        response = (
            self._client.table("vocabulary")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        return [
            VocabEntry(
                id=item["id"],
                user_id=item["user_id"],
                word=item["word"],
                translation=item["translation"],
                context=item.get("context"),
                created_at=item["created_at"],
                reviewed_at=item.get("reviewed_at"),
                practice_count=item.get("practice_count", 0),
            )
            for item in response.data
        ]

    async def get_vocab_count(self, user_id: int) -> int:
        response = (
            self._client.table("vocabulary")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return response.count or 0

    async def practice_word(self, user_id: int, word_id: int) -> None:
        # Primeiro busca o valor atual para incrementar
        response = (
            self._client.table("vocabulary")
            .select("practice_count")
            .eq("id", word_id)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            current_count = response.data[0].get("practice_count", 0)
            self._client.table("vocabulary").update(
                {
                    "practice_count": current_count + 1,
                    "reviewed_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", word_id).eq("user_id", user_id).execute()


def create_database(config) -> BaseDatabase:
    """Factory: retorna a implementacao de BD apropriada."""
    if config.supabase_url and config.supabase_key:
        return SupabaseDatabase(config.supabase_url, config.supabase_key)
    return SQLiteDatabase()
