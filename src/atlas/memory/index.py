from __future__ import annotations

import json
import math
import sqlite3
import struct

from datetime import datetime
from pathlib import Path
from typing import Iterable

from atlas.memory.knowledge import KnowledgeDocument
from atlas.memory.vector import EmbeddingClient


class KnowledgeIndex:
    """
    Persistent semantic knowledge index.

    SQLite stores:
        - document metadata
        - document content
        - serialized embeddings

    Semantic search uses cosine similarity against the local
    embedding model.

    Public API:
        add()
        add_many()
        get()
        search()
        remove()
        delete()
        count()
        clear()
    """

    def __init__(
        self,
        database: str | Path,
        embeddings: EmbeddingClient | None = None,
    ) -> None:

        self.database = Path(database)

        self.database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.embeddings = embeddings or EmbeddingClient()

        self._initialize()

    # ---------------------------------------------------------
    # DATABASE
    # ---------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=30.0,
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )

            connection.commit()

    # ---------------------------------------------------------
    # VECTOR SERIALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def _serialize_vector(
        vector: list[float],
    ) -> bytes:

        if not vector:
            raise ValueError(
                "Cannot serialize an empty embedding"
            )

        return struct.pack(
            f"{len(vector)}f",
            *vector,
        )

    @staticmethod
    def _deserialize_vector(
        data: bytes,
    ) -> list[float]:

        if not data:
            return []

        if len(data) % 4 != 0:
            raise ValueError(
                "Invalid embedding BLOB length"
            )

        count = len(data) // 4

        return list(
            struct.unpack(
                f"{count}f",
                data,
            )
        )

    # ---------------------------------------------------------
    # SIMILARITY
    # ---------------------------------------------------------

    @staticmethod
    def _cosine_similarity(
        left: Iterable[float],
        right: Iterable[float],
    ) -> float:

        left_vector = list(left)
        right_vector = list(right)

        if len(left_vector) != len(right_vector):
            raise ValueError(
                "Embedding dimensions do not match"
            )

        if not left_vector:
            return 0.0

        dot = sum(
            a * b
            for a, b in zip(
                left_vector,
                right_vector,
            )
        )

        left_norm = math.sqrt(
            sum(
                value * value
                for value in left_vector
            )
        )

        right_norm = math.sqrt(
            sum(
                value * value
                for value in right_vector
            )
        )

        if left_norm == 0.0:
            return 0.0

        if right_norm == 0.0:
            return 0.0

        return dot / (
            left_norm * right_norm
        )

    # ---------------------------------------------------------
    # DOCUMENT CONVERSION
    # ---------------------------------------------------------

    @staticmethod
    def _row_to_document(
        row: sqlite3.Row,
    ) -> KnowledgeDocument:

        return KnowledgeDocument(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            source=row["source"],
            tags=json.loads(row["tags"]),
            created=datetime.fromisoformat(
                row["created"]
            ),
            metadata=json.loads(
                row["metadata"]
            ),
        )

    # ---------------------------------------------------------
    # ADD
    # ---------------------------------------------------------

    def add(
        self,
        document: KnowledgeDocument,
    ) -> None:
        """
        Add or replace a knowledge document.

        The document embedding is generated from its content.
        """

        if not document.id:
            raise ValueError(
                "KnowledgeDocument.id cannot be empty"
            )

        if not document.content.strip():
            raise ValueError(
                "KnowledgeDocument.content cannot be empty"
            )

        embedding = self.embeddings.embed(
            document.content
        )

        if not embedding:
            raise ValueError(
                "Embedding service returned an empty vector"
            )

        with self._connect() as connection:

            connection.execute(
                """
                INSERT OR REPLACE INTO documents (
                    id,
                    title,
                    content,
                    source,
                    tags,
                    created,
                    metadata,
                    embedding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.content,
                    document.source,
                    json.dumps(
                        document.tags,
                        ensure_ascii=False,
                    ),
                    document.created.isoformat(),
                    json.dumps(
                        document.metadata,
                        ensure_ascii=False,
                    ),
                    self._serialize_vector(
                        embedding
                    ),
                ),
            )

            connection.commit()

    # ---------------------------------------------------------
    # ADD MANY
    # ---------------------------------------------------------

    def add_many(
        self,
        documents: Iterable[KnowledgeDocument],
    ) -> None:
        """
        Add multiple knowledge documents.
        """

        for document in documents:
            self.add(document)

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get(
        self,
        document_id: str,
    ) -> KnowledgeDocument | None:
        """
        Retrieve a single document by ID.

        Returns None when the document does not exist.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT
                    id,
                    title,
                    content,
                    source,
                    tags,
                    created,
                    metadata,
                    embedding
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_document(row)

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[
        tuple[KnowledgeDocument, float]
    ]:
        """
        Search the knowledge base using cosine similarity.

        Returns:

            [
                (KnowledgeDocument, score),
                ...
            ]

        Results are ordered from highest relevance
        to lowest relevance.
        """

        if not query.strip():
            return []

        if limit <= 0:
            return []

        query_vector = self.embeddings.embed(
            query
        )

        if not query_vector:
            return []

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    content,
                    source,
                    tags,
                    created,
                    metadata,
                    embedding
                FROM documents
                """
            ).fetchall()

        results: list[
            tuple[KnowledgeDocument, float]
        ] = []

        for row in rows:

            document_vector = (
                self._deserialize_vector(
                    row["embedding"]
                )
            )

            score = self._cosine_similarity(
                query_vector,
                document_vector,
            )

            document = self._row_to_document(
                row
            )

            results.append(
                (
                    document,
                    float(score),
                )
            )

        results.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return results[:limit]

    # ---------------------------------------------------------
    # REMOVE
    # ---------------------------------------------------------

    def remove(
        self,
        document_id: str,
    ) -> bool:
        """
        Remove a document by ID.

        Returns:
            True  -> document existed and was removed
            False -> document did not exist
        """

        with self._connect() as connection:

            cursor = connection.execute(
                """
                DELETE FROM documents
                WHERE id = ?
                """,
                (document_id,),
            )

            connection.commit()

            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        document_id: str,
    ) -> bool:
        """
        Backward-compatible alias for remove().
        """

        return self.remove(
            document_id
        )

    # ---------------------------------------------------------
    # COUNT
    # ---------------------------------------------------------

    def count(self) -> int:
        """
        Return the number of indexed documents.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM documents
                """
            ).fetchone()

        return int(row["count"])

    # ---------------------------------------------------------
    # CLEAR
    # ---------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all knowledge documents.
        """

        with self._connect() as connection:

            connection.execute(
                """
                DELETE FROM documents
                """
            )

            connection.commit()
