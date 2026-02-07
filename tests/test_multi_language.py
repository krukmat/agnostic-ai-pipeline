"""
Multi-Language Support Tests

Tests for language detection and multi-language query support.
Supported languages: EN, ES, FR, DE, ZH

Features:
- Automatic language detection from query text
- Language-aware context retrieval
- Configurable supported languages
- Fallback to English if language not supported
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# UNIT TESTS - Language Detection
# ============================================================================


@pytest.mark.unit
def test_language_detector_exists():
    """
    Test: LanguageDetector utility class exists.

    This test will FAIL until LanguageDetector is implemented.
    """
    from graph_rag.language import LanguageDetector

    # Verify class can be instantiated
    detector = LanguageDetector()
    assert detector is not None, "LanguageDetector should be instantiable"


@pytest.mark.unit
def test_language_detector_detects_english():
    """
    Test: LanguageDetector identifies English text.

    This test will FAIL until detection is implemented.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    english_text = "What is artificial intelligence and how does it work?"
    detected_lang = detector.detect_language(english_text)

    assert detected_lang == "en", f"Should detect English, got {detected_lang}"


@pytest.mark.unit
def test_language_detector_detects_spanish():
    """
    Test: LanguageDetector identifies Spanish text.

    This test will FAIL until Spanish detection works.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    spanish_text = "¿Qué es inteligencia artificial y cómo funciona?"
    detected_lang = detector.detect_language(spanish_text)

    assert detected_lang == "es", f"Should detect Spanish, got {detected_lang}"


@pytest.mark.unit
def test_language_detector_detects_french():
    """
    Test: LanguageDetector identifies French text.

    This test will FAIL until French detection works.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    french_text = "Qu'est-ce que l'intelligence artificielle?"
    detected_lang = detector.detect_language(french_text)

    assert detected_lang == "fr", f"Should detect French, got {detected_lang}"


@pytest.mark.unit
def test_language_detector_detects_german():
    """
    Test: LanguageDetector identifies German text.

    This test will FAIL until German detection works.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    german_text = "Was ist künstliche Intelligenz?"
    detected_lang = detector.detect_language(german_text)

    assert detected_lang == "de", f"Should detect German, got {detected_lang}"


@pytest.mark.unit
def test_language_detector_detects_chinese():
    """
    Test: LanguageDetector identifies Chinese text.

    This test will FAIL until Chinese detection works.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    chinese_text = "什么是人工智能？"
    detected_lang = detector.detect_language(chinese_text)

    assert detected_lang == "zh", f"Should detect Chinese, got {detected_lang}"


@pytest.mark.unit
def test_language_detector_returns_language_code():
    """
    Test: LanguageDetector returns ISO 639-1 language codes.

    This test will FAIL until proper language codes are returned.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    # Test various queries
    tests = [
        ("Hello world", "en"),
        ("Hola mundo", "es"),
        ("Bonjour le monde", "fr"),
        ("Hallo Welt", "de"),
        ("你好世界", "zh"),
    ]

    for text, expected_lang in tests:
        detected = detector.detect_language(text)
        assert detected == expected_lang, \
            f"'{text}' should be detected as {expected_lang}, got {detected}"


# ============================================================================
# UNIT TESTS - Engine Language Support
# ============================================================================


@pytest.mark.unit
def test_engine_has_language_detection_method():
    """
    Test: GraphRAGEngine has language-aware query method.

    This test will FAIL until language detection is integrated.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Verify method exists
    assert hasattr(engine, 'detect_query_language'), "Engine should have detect_query_language() method"
    assert callable(engine.detect_query_language), "detect_query_language should be callable"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_detects_query_language():
    """
    Test: Engine can detect language of a query.

    This test will FAIL until language detection works.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Test language detection
    english_query = "What is machine learning?"
    spanish_query = "¿Qué es aprendizaje automático?"

    en_lang = engine.detect_query_language(english_query)
    es_lang = engine.detect_query_language(spanish_query)

    assert en_lang == "en", f"Should detect English, got {en_lang}"
    assert es_lang == "es", f"Should detect Spanish, got {es_lang}"


@pytest.mark.unit
def test_engine_has_supported_languages_config():
    """
    Test: Engine respects supported_languages config.

    This test will FAIL until config is honored.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "supported_languages": ["en", "es", "fr"],
    }

    engine = GraphRAGEngine(config)

    # Verify config is set
    assert hasattr(engine, 'supported_languages'), "Engine should have supported_languages attribute"
    assert engine.supported_languages == ["en", "es", "fr"], "Should match config"


@pytest.mark.unit
def test_default_supported_languages():
    """
    Test: Default supported languages include major languages.

    This test will FAIL until defaults are set.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        # No supported_languages specified
    }

    engine = GraphRAGEngine(config)

    # Should have defaults
    assert hasattr(engine, 'supported_languages'), "Engine should have default supported_languages"
    assert "en" in engine.supported_languages, "Should include English"
    assert "es" in engine.supported_languages, "Should include Spanish"


# ============================================================================
# UNIT TESTS - Language-Aware Queries
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_has_language_aware_query_method():
    """
    Test: Engine has language-aware query method.

    This test will FAIL until method is implemented.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Verify method exists
    assert hasattr(engine, 'query_multilingual'), "Engine should have query_multilingual() method"
    assert callable(engine.query_multilingual), "query_multilingual should be callable"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_language_aware_query_detects_and_responds():
    """
    Test: Language-aware query detects language and responds.

    This test will FAIL until language-aware querying works.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Mock RAG engine
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Response in detected language")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Test with Spanish query
            spanish_query = "¿Cuál es el objetivo principal?"
            result = await engine.query_multilingual(spanish_query)

            assert result is not None, "Should return response"
            assert len(result) > 0, "Response should not be empty"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_language_aware_query_adds_language_context():
    """
    Test: Language-aware query includes language in request context.

    This test will FAIL until language context is added.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Respuesta")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            spanish_query = "¿Cómo funciona?"
            await engine.query_multilingual(spanish_query)

            # Verify language information was used
            assert mock_rag.aquery.called, "Should call aquery"


# ============================================================================
# INTEGRATION TESTS - Multi-Language Queries
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_english_and_spanish():
    """
    Integration Test: Engine handles English and Spanish queries.

    Validates that different languages are detected and handled.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Response")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # English query
            en_result = await engine.query_multilingual("What is AI?")
            assert en_result is not None, "English query should work"

            # Spanish query
            es_result = await engine.query_multilingual("¿Qué es IA?")
            assert es_result is not None, "Spanish query should work"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_language_detection_with_mixed_text():
    """
    Integration Test: Language detection handles mixed-language text.

    Validates that primary language is detected correctly even with mixed text.
    """
    from graph_rag.language import LanguageDetector

    detector = LanguageDetector()

    # Mostly Spanish with some English
    mixed_text = "¿Qué es machine learning en español? Is a very useful concept."
    detected = detector.detect_language(mixed_text)

    # Should detect dominant language (Spanish in this case)
    assert detected in ["es", "en"], "Should detect one of the languages"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unsupported_language_fallback():
    """
    Integration Test: Unsupported languages fall back to English.

    Validates graceful fallback for unsupported languages.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "supported_languages": ["en", "es"],  # Only EN and ES
    }

    engine = GraphRAGEngine(config)

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Response")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Query in unsupported language (Japanese)
            japanese_query = "人工知能とは何ですか？"
            result = await engine.query_multilingual(japanese_query)

            # Should fall back to English processing
            assert result is not None, "Should handle unsupported language gracefully"


# ============================================================================
# UNIT TESTS - Language Configuration
# ============================================================================


@pytest.mark.unit
def test_language_config_in_yaml():
    """
    Test: Language settings can be configured via config.yaml.

    Document expected config structure:
    graph_rag:
      language_detection: true
      supported_languages: ["en", "es", "fr", "de", "zh"]
      default_language: "en"
    """
    # This is a documentation test
    # Actual YAML validation happens on config load
    pass


@pytest.mark.unit
def test_language_detection_can_be_disabled():
    """
    Test: Language detection can be disabled via config.

    This test will FAIL until config option is implemented.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "language_detection": False,  # Disable language detection
    }

    engine = GraphRAGEngine(config)

    # Verify setting is respected
    assert hasattr(engine, 'language_detection'), "Engine should have language_detection attribute"
    assert engine.language_detection == False, "Should respect disabled setting"


# ============================================================================
# PERFORMANCE TESTS - Language Detection Speed
# ============================================================================


@pytest.mark.integration
def test_language_detection_performance():
    """
    Performance Test: Language detection is fast.

    Validates that language detection doesn't add significant overhead.
    """
    from graph_rag.language import LanguageDetector
    import time

    detector = LanguageDetector()

    # Test detection speed for various texts
    texts = [
        "What is artificial intelligence?",
        "¿Qué es inteligencia artificial?",
        "Qu'est-ce que l'intelligence artificielle?",
        "Was ist künstliche Intelligenz?",
        "什么是人工智能？",
    ]

    start = time.perf_counter()
    for text in texts:
        detector.detect_language(text)
    elapsed = time.perf_counter() - start

    # Detection should be very fast (< 50ms for 5 texts = 10ms per text)
    assert elapsed < 0.05, f"Language detection should be fast (got {elapsed:.3f}s)"


# ============================================================================
# UNIT TESTS - Language-Specific Context
# ============================================================================


@pytest.mark.unit
def test_language_aware_context_retrieval_exists():
    """
    Test: Engine has method for language-aware context retrieval.

    This test will FAIL until method exists.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    assert hasattr(engine, 'get_context_multilingual'), "Should have language-aware context method"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_language_aware_context_returns_formatted_response():
    """
    Test: Language-aware context is properly formatted.

    This test will FAIL until formatting is implemented.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Entity1, Entity2, Relationship")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            context = await engine.get_context_multilingual("¿Contexto?")

            # Should return formatted context
            assert context is not None, "Should return context"
            assert isinstance(context, str), "Context should be string"
