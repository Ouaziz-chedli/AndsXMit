"""
Unit tests for the vector_store module.

Tests ChromaDB integration for disease case storage and retrieval.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.vector_store import (
    VectorStore,
    RetrievedCase,
    StoredCase,
    reset_vector_store,
)


@pytest.fixture
def temp_vector_store():
    """Create a temporary vector store for testing."""
    temp_dir = tempfile.mkdtemp()
    store = VectorStore(persist_directory=temp_dir)
    yield store
    # Cleanup
    shutil.rmtree(temp_dir)
    reset_vector_store()


@pytest.fixture
def mock_positive_case():
    """Create a mock positive case for testing."""
    return StoredCase(
        case_id="test_pos_001",
        disease_id="down_syndrome",
        trimester="1st",
        is_positive=True,
        embedding=[0.1] * 10,  # Small embedding for testing
        symptom_text="nuchal_translucency_3_5mm absent_nasal_bone",
        gestational_age_weeks=12.0,
        b_hcg_mom=2.1,
        papp_a_mom=0.48,
    )


@pytest.fixture
def mock_negative_case():
    """Create a mock negative case for testing."""
    return StoredCase(
        case_id="test_neg_001",
        disease_id="down_syndrome",
        trimester="1st",
        is_positive=False,
        embedding=[0.9] * 10,  # Different embedding
        symptom_text="nuchal_translucency_1_8mm nasal_bone_present",
        gestational_age_weeks=12.0,
        b_hcg_mom=1.0,
        papp_a_mom=1.0,
    )


class TestVectorStoreInit:
    """Tests for VectorStore initialization."""

    def test_initialization_with_default_path(self):
        """Test initialization with default path."""
        store = VectorStore()
        assert store is not None
        assert store.client is not None

    def test_initialization_with_custom_path(self, temp_vector_store):
        """Test initialization with custom path."""
        store = VectorStore(persist_directory="/custom/path")
        assert store is not None


class TestVectorStoreCollections:
    """Tests for collection management."""

    def test_get_or_create_collection(self, temp_vector_store):
        """Test getting or creating a collection."""
        collection = temp_vector_store.get_or_create_collection(
            disease_id="down_syndrome",
            trimester="1st"
        )
        assert collection is not None
        assert collection.name == "down_syndrome_1st"

    def test_collection_name_format(self, temp_vector_store):
        """Test collection name generation."""
        # Test multiple disease/trimester combinations
        combinations = [
            ("down_syndrome", "1st", "down_syndrome_1st"),
            ("cardiac_defect", "2nd", "cardiac_defect_2nd"),
            ("complex_disease_name", "3rd", "complex_disease_name_3rd"),
        ]

        for disease, trimester, expected_name in combinations:
            collection = temp_vector_store.get_or_create_collection(disease, trimester)
            assert collection.name == expected_name

    def test_retrieve_existing_collection(self, temp_vector_store):
        """Test that retrieving an existing collection works."""
        # Create collection
        temp_vector_store.get_or_create_collection("down_syndrome", "1st")

        # Retrieve same collection
        collection = temp_vector_store.get_or_create_collection("down_syndrome", "1st")

        assert collection.name == "down_syndrome_1st"

    def test_list_collections(self, temp_vector_store):
        """Test listing all collections."""
        # Create multiple collections
        temp_vector_store.get_or_create_collection("down_syndrome", "1st")
        temp_vector_store.get_or_create_collection("down_syndrome", "2nd")
        temp_vector_store.get_or_create_collection("cardiac_defect", "1st")

        collections = temp_vector_store.list_collections()

        assert len(collections) >= 3
        assert "down_syndrome_1st" in collections
        assert "down_syndrome_2nd" in collections
        assert "cardiac_defect_1st" in collections

    def test_delete_collection(self, temp_vector_store):
        """Test deleting a collection."""
        # Create collection
        temp_vector_store.get_or_create_collection("down_syndrome", "1st")

        # Verify it exists
        assert "down_syndrome_1st" in temp_vector_store.list_collections()

        # Delete it
        temp_vector_store.delete_collection("down_syndrome", "1st")

        # Verify it's gone
        assert "down_syndrome_1st" not in temp_vector_store.list_collections()

    def test_delete_nonexistent_collection(self, temp_vector_store):
        """Test deleting a nonexistent collection (should not error)."""
        # Should not raise an error
        temp_vector_store.delete_collection("nonexistent", "1st")


class TestAddCase:
    """Tests for adding cases to vector store."""

    def test_add_single_case(self, temp_vector_store, mock_positive_case):
        """Test adding a single case."""
        temp_vector_store.add_case(mock_positive_case)

        count = temp_vector_store.get_case_count("down_syndrome", "1st")
        assert count == 1

    def test_add_multiple_cases(self, temp_vector_store, mock_positive_case, mock_negative_case):
        """Test adding multiple cases."""
        temp_vector_store.add_case(mock_positive_case)
        temp_vector_store.add_case(mock_negative_case)

        count = temp_vector_store.get_case_count("down_syndrome", "1st")
        assert count == 2

    def test_add_cases_batch(self, temp_vector_store):
        """Test adding cases in batch."""
        cases = [
            StoredCase(
                case_id=f"test_{i}",
                disease_id="down_syndrome",
                trimester="1st",
                is_positive=i % 2 == 0,
                embedding=[i * 0.1] * 10,
                symptom_text=f"symptom_{i}",
                gestational_age_weeks=12.0,
            )
            for i in range(10)
        ]

        temp_vector_store.add_cases(cases)

        count = temp_vector_store.get_case_count("down_syndrome", "1st")
        assert count == 10

    def test_case_metadata_preserved(self, temp_vector_store, mock_positive_case):
        """Test that case metadata is preserved."""
        temp_vector_store.add_case(mock_positive_case)

        # Search for the case
        results = temp_vector_store.search_disease(
            query_embedding=mock_positive_case.embedding,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=1,
        )

        assert len(results) == 1
        retrieved = results[0]

        assert retrieved.case_id == mock_positive_case.case_id
        assert retrieved.is_positive == mock_positive_case.is_positive
        assert retrieved.similarity > 0.9  # Should be very similar to itself


class TestSearchDisease:
    """Tests for searching disease cases."""

    def test_search_with_no_results(self, temp_vector_store):
        """Test search when no matching cases exist."""
        query_embedding = [0.5] * 10

        results = temp_vector_store.search_disease(
            query_embedding=query_embedding,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=5,
        )

        assert len(results) == 0

    def test_search_with_results(self, temp_vector_store, mock_positive_case, mock_negative_case):
        """Test search with matching cases."""
        # Add cases
        temp_vector_store.add_case(mock_positive_case)
        temp_vector_store.add_case(mock_negative_case)

        # Search
        query_embedding = [0.1] * 10  # Similar to positive case
        results = temp_vector_store.search_disease(
            query_embedding=query_embedding,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=2,
        )

        assert len(results) == 2

    def test_search_top_k(self, temp_vector_store):
        """Test that top_k parameter limits results."""
        # Add multiple cases
        for i in range(10):
            case = StoredCase(
                case_id=f"test_{i}",
                disease_id="down_syndrome",
                trimester="1st",
                is_positive=True,
                embedding=[i * 0.1] * 10,
                symptom_text=f"symptom_{i}",
                gestational_age_weeks=12.0,
            )
            temp_vector_store.add_case(case)

        # Search for top 3
        results = temp_vector_store.search_disease(
            query_embedding=[0.5] * 10,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=3,
        )

        assert len(results) == 3

    def test_search_filter_positive(self, temp_vector_store, mock_positive_case, mock_negative_case):
        """Test filtering for positive cases only."""
        temp_vector_store.add_case(mock_positive_case)
        temp_vector_store.add_case(mock_negative_case)

        # Search for positive only
        results = temp_vector_store.search_disease(
            query_embedding=[0.1] * 10,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=10,
            filter_positive=True,
        )

        assert len(results) == 1
        assert results[0].is_positive is True

    def test_search_filter_negative(self, temp_vector_store, mock_positive_case, mock_negative_case):
        """Test filtering for negative cases only."""
        temp_vector_store.add_case(mock_positive_case)
        temp_vector_store.add_case(mock_negative_case)

        # Search for negative only
        results = temp_vector_store.search_disease(
            query_embedding=[0.9] * 10,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=10,
            filter_positive=False,
        )

        assert len(results) == 1
        assert results[0].is_positive is False

    def test_similarity_scores(self, temp_vector_store, mock_positive_case):
        """Test that similarity scores are calculated correctly."""
        temp_vector_store.add_case(mock_positive_case)

        # Search with identical embedding (should have similarity = 1.0)
        results = temp_vector_store.search_disease(
            query_embedding=mock_positive_case.embedding,
            disease_id="down_syndrome",
            trimester="1st",
            top_k=1,
        )

        assert len(results) == 1
        # Should be very close to 1.0 (exact match)
        assert results[0].similarity > 0.99


class TestGetCaseCount:
    """Tests for getting case counts."""

    def test_empty_collection(self, temp_vector_store):
        """Test count for empty collection."""
        count = temp_vector_store.get_case_count("down_syndrome", "1st")
        assert count == 0

    def test_nonempty_collection(self, temp_vector_store):
        """Test count for collection with cases."""
        for i in range(5):
            case = StoredCase(
                case_id=f"test_{i}",
                disease_id="down_syndrome",
                trimester="1st",
                is_positive=True,
                embedding=[i * 0.1] * 10,
                symptom_text=f"symptom_{i}",
                gestational_age_weeks=12.0,
            )
            temp_vector_store.add_case(case)

        count = temp_vector_store.get_case_count("down_syndrome", "1st")
        assert count == 5

    def test_separate_collections(self, temp_vector_store):
        """Test that different collections have separate counts."""
        # Add to first collection
        temp_vector_store.add_case(StoredCase(
            case_id="test_1",
            disease_id="down_syndrome",
            trimester="1st",
            is_positive=True,
            embedding=[0.1] * 10,
            symptom_text="test",
            gestational_age_weeks=12.0,
        ))

        # Add to second collection
        temp_vector_store.add_case(StoredCase(
            case_id="test_2",
            disease_id="down_syndrome",
            trimester="2nd",
            is_positive=True,
            embedding=[0.1] * 10,
            symptom_text="test",
            gestational_age_weeks=20.0,
        ))

        # Verify separate counts
        count_1st = temp_vector_store.get_case_count("down_syndrome", "1st")
        count_2nd = temp_vector_store.get_case_count("down_syndrome", "2nd")

        assert count_1st == 1
        assert count_2nd == 1


class TestRetrievedCase:
    """Tests for RetrievedCase dataclass."""

    def test_creation(self):
        """Test creating a RetrievedCase."""
        case = RetrievedCase(
            case_id="test_001",
            similarity=0.85,
            is_positive=True,
            disease_id="down_syndrome",
            trimester="1st",
            symptom_text="nt_3_5mm absent_nasal_bone",
            metadata={"b_hcg_mom": 2.1},
        )

        assert case.case_id == "test_001"
        assert case.similarity == 0.85
        assert case.is_positive is True

    def test_optional_fields(self):
        """Test optional fields can be None."""
        case = RetrievedCase(
            case_id="test_001",
            similarity=0.5,
            is_positive=False,
            disease_id="down_syndrome",
            trimester="1st",
        )

        assert case.symptom_text is None
        assert case.metadata is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
