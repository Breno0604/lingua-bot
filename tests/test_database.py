"""
LinguaBot --- Tests for bot.database

Tests both SQLiteDatabase and SupabaseDatabase implementations
against the BaseDatabase interface.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.database import (
    BaseDatabase,
    SQLiteDatabase,
    SupabaseDatabase,
    VocabEntry,
    UserPreferences,
    create_database,
)


class TestVocabEntry:
    """Tests for VocabEntry dataclass."""

    def test_minimal_creation(self):
        entry = VocabEntry(id=1, user_id=123, word="hello", translation="ola",
                           context="", created_at="2026-01-01", reviewed_at=None,
                           practice_count=0)
        assert entry.word == "hello"
        assert entry.level == "A1"

    def test_with_level(self):
        entry = VocabEntry(id=2, user_id=123, word="goodbye", translation="tchau",
                           context="", created_at="2026-01-01", reviewed_at=None,
                           practice_count=0, level="B1")
        assert entry.level == "B1"


class TestUserPreferences:
    """Tests for UserPreferences dataclass."""

    def test_defaults(self):
        prefs = UserPreferences(user_id=123)
        assert prefs.level == "A1"
        assert prefs.voice_id is None
        assert prefs.tts_speed is None

    def test_custom_values(self):
        prefs = UserPreferences(user_id=123, level="B1", voice_id="custom", tts_speed=0.85)
        assert prefs.level == "B1"
        assert prefs.voice_id == "custom"
        assert prefs.tts_speed == 0.85


class TestSQLiteDatabase:
    """Integration tests for SQLiteDatabase using a temp file."""

    @pytest.fixture
    def db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        db = SQLiteDatabase(db_path=db_path)
        yield db
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_save_and_get_vocab(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola", context="Hello there!", level="A1")
        entries = await db.get_vocab(user_id=123)
        assert len(entries) == 1
        assert entries[0].word == "hello"
        assert entries[0].translation == "ola"
        assert entries[0].context == "Hello there!"
        assert entries[0].level == "A1"

    @pytest.mark.asyncio
    async def test_save_vocab_case_insensitive(self, db):
        await db.save_vocab(user_id=123, word="HELLO", translation="ola")
        entries = await db.get_vocab(user_id=123)
        assert entries[0].word == "hello"

    @pytest.mark.asyncio
    async def test_save_duplicate_vocab_ignored(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola")
        await db.save_vocab(user_id=123, word="hello", translation="ola denovo")
        entries = await db.get_vocab(user_id=123)
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_get_vocab_empty(self, db):
        entries = await db.get_vocab(user_id=999)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_vocab_pagination(self, db):
        for i in range(15):
            await db.save_vocab(user_id=123, word=f"word{i}", translation=f"traducao{i}")
        page1 = await db.get_vocab(user_id=123, page=1, page_size=10)
        page2 = await db.get_vocab(user_id=123, page=2, page_size=10)
        assert len(page1) == 10
        assert len(page2) == 5

    @pytest.mark.asyncio
    async def test_get_vocab_filtered_by_level(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola", level="A1")
        await db.save_vocab(user_id=123, word="goodbye", translation="tchau", level="B1")
        a1_entries = await db.get_vocab(user_id=123, level="A1")
        b1_entries = await db.get_vocab(user_id=123, level="B1")
        assert len(a1_entries) == 1
        assert len(b1_entries) == 1
        assert a1_entries[0].word == "hello"
        assert b1_entries[0].word == "goodbye"

    @pytest.mark.asyncio
    async def test_get_vocab_count(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola")
        await db.save_vocab(user_id=123, word="goodbye", translation="tchau")
        count = await db.get_vocab_count(user_id=123)
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_vocab_count_filtered(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola", level="A1")
        await db.save_vocab(user_id=123, word="goodbye", translation="tchau", level="B1")
        count = await db.get_vocab_count(user_id=123, level="A1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_vocab_count_zero(self, db):
        count = await db.get_vocab_count(user_id=999)
        assert count == 0

    @pytest.mark.asyncio
    async def test_practice_word(self, db):
        await db.save_vocab(user_id=123, word="hello", translation="ola")
        entries = await db.get_vocab(user_id=123)
        word_id = entries[0].id
        await db.practice_word(user_id=123, word_id=word_id)
        entries = await db.get_vocab(user_id=123)
        assert entries[0].practice_count == 1

    @pytest.mark.asyncio
    async def test_user_preferences_default(self, db):
        prefs = await db.get_user_preferences(user_id=999)
        assert prefs.user_id == 999
        assert prefs.level == "A1"
        assert prefs.voice_id is None
        assert prefs.tts_speed is None

    @pytest.mark.asyncio
    async def test_set_and_get_user_preferences(self, db):
        await db.set_user_preferences(user_id=123, level="B1", voice_id="custom", tts_speed=0.85)
        prefs = await db.get_user_preferences(user_id=123)
        assert prefs.level == "B1"
        assert prefs.voice_id == "custom"
        assert prefs.tts_speed == 0.85

    @pytest.mark.asyncio
    async def test_set_user_preferences_partial(self, db):
        await db.set_user_preferences(user_id=123, level="A2")
        prefs = await db.get_user_preferences(user_id=123)
        assert prefs.level == "A2"
        assert prefs.voice_id is None
        assert prefs.tts_speed is None

    @pytest.mark.asyncio
    async def test_set_user_preferences_upsert(self, db):
        await db.set_user_preferences(user_id=123, level="A2")
        await db.set_user_preferences(user_id=123, tts_speed=0.75)
        prefs = await db.get_user_preferences(user_id=123)
        assert prefs.level == "A2"
        assert prefs.tts_speed == 0.75


class TestSupabaseDatabase:
    """Tests for SupabaseDatabase using mocked client."""

    @pytest.fixture
    def mock_supabase(self):
        with patch.dict("sys.modules", {"supabase": MagicMock()}):
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_select
            mock_select.order.return_value = mock_select
            mock_select.range.return_value = mock_select
            yield mock_client, mock_table, mock_select

    @pytest.fixture
    def db(self, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        sdb = SupabaseDatabase(supabase_url="https://test.supabase.co", supabase_key="test_key")
        sdb._client = mock_client
        return sdb

    @pytest.mark.asyncio
    async def test_save_vocab(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        await db.save_vocab(user_id=123, word="hello", translation="ola", context="Hi!", level="A1")
        mock_client.table.assert_called_with("vocabulary")
        # Check upsert was called
        upsert_calls = [c for c in mock_table.method_calls if c[0] == 'upsert']
        assert len(upsert_calls) > 0

    @pytest.mark.asyncio
    async def test_get_vocab_empty(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[])
        entries = await db.get_vocab(user_id=123)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_vocab_with_data(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[{
            "id": 1, "user_id": 123, "word": "hello", "translation": "ola",
            "context": "Hello!", "created_at": "2026-01-01",
            "reviewed_at": None, "practice_count": 3, "level": "A1",
        }])
        entries = await db.get_vocab(user_id=123)
        assert len(entries) == 1
        assert entries[0].word == "hello"

    @pytest.mark.asyncio
    async def test_get_vocab_count(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(count=5)
        count = await db.get_vocab_count(user_id=123)
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_vocab_count_zero(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(count=0)
        count = await db.get_vocab_count(user_id=123)
        assert count == 0

    @pytest.mark.asyncio
    async def test_practice_word(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[{"practice_count": 2}])
        await db.practice_word(user_id=123, word_id=1)
        update_calls = [c for c in mock_table.method_calls if c[0] == 'update']
        assert len(update_calls) > 0

    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[])
        prefs = await db.get_user_preferences(user_id=999)
        assert prefs.user_id == 999
        assert prefs.level == "A1"

    @pytest.mark.asyncio
    async def test_get_user_preferences_existing(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[{
            "user_id": 123, "level": "B1", "voice_id": "custom", "tts_speed": 0.85,
        }])
        prefs = await db.get_user_preferences(user_id=123)
        assert prefs.level == "B1"
        assert prefs.voice_id == "custom"
        assert prefs.tts_speed == 0.85

    @pytest.mark.asyncio
    async def test_set_user_preferences(self, db, mock_supabase):
        mock_client, mock_table, mock_select = mock_supabase
        mock_select.execute.return_value = MagicMock(data=[])
        await db.set_user_preferences(user_id=123, level="B1")
        upsert_calls = [c for c in mock_table.method_calls if c[0] == 'upsert']
        assert len(upsert_calls) > 0


class TestCreateDatabase:
    """Tests for the create_database factory function."""

    class FakeConfig:
        def __init__(self, supabase_url="", supabase_key=""):
            self.supabase_url = supabase_url
            self.supabase_key = supabase_key

    def test_create_sqlite_when_no_supabase(self):
        config = self.FakeConfig()
        db = create_database(config)
        assert isinstance(db, SQLiteDatabase)

    @patch("bot.database.SupabaseDatabase")
    def test_create_supabase_when_configured(self, mock_supabase_cls):
        config = self.FakeConfig(supabase_url="https://test.supabase.co", supabase_key="test_key")
        db = create_database(config)
        mock_supabase_cls.assert_called_once_with("https://test.supabase.co", "test_key")
