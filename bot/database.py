"""
LinguaBot --- Database Abstraction Layer

Suporta dois modos:
  - SQLiteDatabase (dev local, sem configuracao)
  - SupabaseDatabase (producao no Render, usando supabase-py)

A escolha e feita automaticamente baseada na presenca de SUPABASE_URL.
"""

from __future__ import annotations

import logging
import sqlite3
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


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
    level: str = "A1"


@dataclass
class UserPreferences:
    """Preferencias do usuario persistidas em banco."""
    user_id: int
    level: str = "A1"
    voice_id: Optional[str] = None
    tts_speed: Optional[float] = None


class BaseDatabase(ABC):
    """Interface abstrata para operacoes de banco de dados."""

    @abstractmethod
    async def save_vocab(
        self,
        user_id: int,
        word: str,
        translation: str,
        context: str = "",
        level: str = "A1",
    ) -> None:
        """Salva uma nova palavra no vocabulario do usuario."""
        ...

    @abstractmethod
    async def get_vocab(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        level: Optional[str] = None,
    ) -> list[VocabEntry]:
        """Retorna o vocabulario do usuario com paginacao."""
        ...

    @abstractmethod
    async def get_vocab_count(
        self,
        user_id: int,
        level: Optional[str] = None,
    ) -> int:
        """Retorna o total de palavras aprendidas pelo usuario."""
        ...

    @abstractmethod
    async def practice_word(self, user_id: int, word_id: int) -> None:
        """Incrementa o contador de pratica de uma palavra."""
        ...

    @abstractmethod
    async def get_user_preferences(self, user_id: int) -> UserPreferences:
        """Retorna as preferencias do usuario."""
        ...

    @abstractmethod
    async def set_user_preferences(
        self,
        user_id: int,
        level: Optional[str] = None,
        voice_id: Optional[str] = None,
        tts_speed: Optional[float] = None,
    ) -> None:
        """Atualiza as preferencias do usuario (so os campos fornecidos)."""
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
                    level TEXT NOT NULL DEFAULT 'A1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    practice_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, word)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    level TEXT NOT NULL DEFAULT 'A1',
                    voice_id TEXT,
                    tts_speed REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    async def save_vocab(
        self,
        user_id: int,
        word: str,
        translation: str,
        context: str = "",
        level: str = "A1",
    ) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO vocabulary
                   (user_id, word, translation, context, level)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    word.lower().strip(),
                    translation.strip(),
                    context,
                    level.upper().strip(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def get_vocab(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        level: Optional[str] = None,
    ) -> list[VocabEntry]:
        offset = (page - 1) * page_size
        conn = self._get_connection()
        try:
            if level:
                rows = conn.execute(
                    """SELECT * FROM vocabulary
                       WHERE user_id = ? AND level = ?
                       ORDER BY created_at DESC
                       LIMIT ? OFFSET ?""",
                    (user_id, level.upper(), page_size, offset),
                ).fetchall()
            else:
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
                    level=row["level"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    async def get_vocab_count(
        self,
        user_id: int,
        level: Optional[str] = None,
    ) -> int:
        conn = self._get_connection()
        try:
            if level:
                row = conn.execute(
                    "SELECT COUNT(*) as total FROM vocabulary WHERE user_id = ? AND level = ?",
                    (user_id, level.upper()),
                ).fetchone()
            else:
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

    async def get_user_preferences(self, user_id: int) -> UserPreferences:
        """Retorna as preferencias do usuario (defaults se nao existir)."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row:
                return UserPreferences(
                    user_id=row["user_id"],
                    level=row["level"],
                    voice_id=row["voice_id"],
                    tts_speed=row["tts_speed"],
                )
            return UserPreferences(user_id=user_id)
        finally:
            conn.close()

    async def set_user_preferences(
        self,
        user_id: int,
        level: Optional[str] = None,
        voice_id: Optional[str] = None,
        tts_speed: Optional[float] = None,
    ) -> None:
        """Atualiza as preferencias do usuario (UPSERT)."""
        conn = self._get_connection()
        try:
            # Primeiro, pega valores existentes para nao sobrescrever com None
            current = await self.get_user_preferences(user_id)
            new_level = level if level is not None else current.level
            new_voice = voice_id if voice_id is not None else current.voice_id
            new_speed = tts_speed if tts_speed is not None else current.tts_speed

            conn.execute(
                """INSERT INTO user_preferences (user_id, level, voice_id, tts_speed, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id) DO UPDATE SET
                       level = excluded.level,
                       voice_id = excluded.voice_id,
                       tts_speed = excluded.tts_speed,
                       updated_at = CURRENT_TIMESTAMP""",
                (user_id, new_level, new_voice, new_speed),
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
        self,
        user_id: int,
        word: str,
        translation: str,
        context: str = "",
        level: str = "A1",
    ) -> None:
        try:
            data = {
                "user_id": user_id,
                "word": word.lower().strip(),
                "translation": translation.strip(),
                "context": context,
                "level": level.upper().strip(),
            }
            self._client.table("vocabulary").upsert(
                data, on_conflict=["user_id", "word"]
            ).execute()
        except Exception as e:
            logger.error("Erro ao salvar vocabulario no Supabase: %s", e)

    async def get_vocab(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        level: Optional[str] = None,
    ) -> list[VocabEntry]:
        try:
            offset = (page - 1) * page_size
            query = (
                self._client.table("vocabulary")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
            )
            if level:
                query = query.eq("level", level.upper())

            response = query.range(offset, offset + page_size - 1).execute()

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
                    level=item.get("level", "A1"),
                )
                for item in response.data
            ]
        except Exception as e:
            logger.error("Erro ao buscar vocabulario no Supabase: %s", e)
            return []

    async def get_vocab_count(
        self,
        user_id: int,
        level: Optional[str] = None,
    ) -> int:
        try:
            query = (
                self._client.table("vocabulary")
                .select("id", count="exact")
                .eq("user_id", user_id)
            )
            if level:
                query = query.eq("level", level.upper())

            response = query.execute()
            return response.count or 0
        except Exception as e:
            logger.error("Erro ao contar vocabulario no Supabase: %s", e)
            return 0

    async def practice_word(self, user_id: int, word_id: int) -> None:
        try:
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
                        "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", word_id).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error("Erro ao praticar palavra no Supabase: %s", e)

    async def get_user_preferences(self, user_id: int) -> UserPreferences:
        """Retorna as preferencias do usuario do Supabase."""
        try:
            response = (
                self._client.table("user_preferences")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if response.data:
                item = response.data[0]
                return UserPreferences(
                    user_id=item["user_id"],
                    level=item.get("level", "A1"),
                    voice_id=item.get("voice_id"),
                    tts_speed=item.get("tts_speed"),
                )
            return UserPreferences(user_id=user_id)
        except Exception as e:
            logger.error("Erro ao buscar preferencias: %s", e)
            return UserPreferences(user_id=user_id)

    async def set_user_preferences(
        self,
        user_id: int,
        level: Optional[str] = None,
        voice_id: Optional[str] = None,
        tts_speed: Optional[float] = None,
    ) -> None:
        """Atualiza as preferencias do usuario no Supabase (upsert)."""
        try:
            current = await self.get_user_preferences(user_id)
            data = {
                "user_id": user_id,
                "level": level if level is not None else current.level,
                "voice_id": voice_id if voice_id is not None else current.voice_id,
                "tts_speed": tts_speed if tts_speed is not None else current.tts_speed,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("user_preferences").upsert(
                data, on_conflict=["user_id"]
            ).execute()
        except Exception as e:
            logger.error("Erro ao salvar preferencias: %s", e)


def create_database(config) -> BaseDatabase:
    """Factory: retorna a implementacao de BD apropriada."""
    if config.supabase_url and config.supabase_key:
        return SupabaseDatabase(config.supabase_url, config.supabase_key)
    return SQLiteDatabase()
