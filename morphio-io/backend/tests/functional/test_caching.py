import hashlib
import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import AnyHttpUrl

from app.services.video import process_video
from app.utils.cache_utils import (
    CACHE_VERSION,
    cache_generated_content,
    cache_generated_title,
    cache_key_builder,
    cache_whisper_transcription,
    cache_youtube_transcript,
    compute_template_hash,
    get_cache,
    get_cached_generated_content,
    get_cached_generated_title,
    get_cached_whisper_transcription,
    get_cached_youtube_transcript,
    get_redis_data,
    invalidate_cache,
    set_cache,
    set_redis_data,
)
from app.utils.file_utils import compute_hash
from schemas.media_schema import MediaProcessingInput, MediaSource, MediaType

TEST_VIDEO_FILE = os.path.join(os.path.dirname(__file__), "test_video.mp4")


# Mock Redis client
@pytest.fixture
async def mock_redis():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=True)
    mock_client.exists = AsyncMock(return_value=False)

    with (
        patch("app.utils.cache_utils._redis_client", mock_client),
        patch("app.utils.cache_utils.is_redis_available", return_value=True),
    ):
        yield mock_client


@pytest.mark.asyncio
async def test_set_and_get_cache(mock_redis):
    key = "test_key"
    value = "test_value"

    # Test set_cache
    mock_redis.set = AsyncMock()
    await set_cache(key, value)
    mock_redis.set.assert_called_once_with(key, json.dumps(value), ex=3600)

    # Test get_cache
    mock_redis.get = AsyncMock(return_value=json.dumps(value))
    result = await get_cache(key)
    assert result == json.dumps(value)
    mock_redis.get.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_redis_utils(mock_redis):
    key = "test_key"
    value = "test_value"

    # Test set_redis_data
    await set_redis_data(key, value)
    # set_redis_data serializes the value with json.dumps
    mock_redis.set.assert_called_once_with(key, json.dumps(value), ex=3600)

    # Test get_redis_data
    mock_redis.get.return_value = value
    result = await get_redis_data(key)
    assert result == value
    mock_redis.get.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_cache_key_builder():
    prefix = "test"
    args = ["arg1", "arg2", 3]
    expected_key = f"v{CACHE_VERSION}:test:arg1:arg2:3"
    assert cache_key_builder(prefix, *args) == expected_key


@pytest.mark.asyncio
async def test_youtube_transcript_caching(mock_redis):
    video_id = "test_video_id"
    transcript = "This is a test transcript"

    # Test caching
    await cache_youtube_transcript(video_id, transcript)
    mock_redis.set.assert_called_once()

    # Test retrieval
    mock_redis.get.return_value = json.dumps(transcript)
    result = await get_cached_youtube_transcript(video_id)
    assert result == json.dumps({"text": transcript})


@pytest.mark.asyncio
async def test_whisper_transcription_caching(mock_redis):
    file_hash = "test_file_hash"
    transcription = "This is a test whisper transcription"

    # Test caching
    await cache_whisper_transcription(file_hash, transcription)
    mock_redis.set.assert_called_once()

    # Test retrieval
    mock_redis.get.return_value = json.dumps(transcription)
    result = await get_cached_whisper_transcription(file_hash)
    assert result == json.dumps({"text": transcription})


@pytest.mark.asyncio
async def test_cached_transcription_legacy_double_encoded_normalizes(mock_redis):
    file_hash = "legacy_file_hash"
    legacy_value = json.dumps(json.dumps({"text": "Legacy transcript"}))

    mock_redis.get.return_value = legacy_value
    result = await get_cached_whisper_transcription(file_hash)

    assert result == json.dumps({"text": "Legacy transcript"})


@pytest.mark.asyncio
async def test_generated_content_caching(mock_redis):
    transcript_hash = "test_transcript_hash"
    template_id = "test_template_id"
    template_hash = "test_template_hash"
    user_id = 1
    model_name = "test_model"
    content = "This is test generated content"

    # Test caching
    await cache_generated_content(
        transcript_hash, template_id, template_hash, user_id, content, model_name
    )
    mock_redis.set.assert_called_once()

    # Test retrieval
    mock_redis.get.return_value = json.dumps(content)
    result = await get_cached_generated_content(
        transcript_hash, template_id, template_hash, user_id, model_name
    )
    assert result == json.dumps(content)


@pytest.mark.asyncio
async def test_generated_title_caching(mock_redis):
    content_hash = "test_content_hash"
    title = "Test Generated Title"

    # Test caching
    await cache_generated_title(content_hash, title)
    mock_redis.set.assert_called_once()

    # Test retrieval
    mock_redis.get.return_value = json.dumps(title)
    result = await get_cached_generated_title(content_hash)
    assert result == json.dumps(title)


@pytest.mark.asyncio
async def test_process_video_with_caching(mock_redis):
    # Mock dependencies
    mock_db = AsyncMock()
    mock_update_job_status = AsyncMock()
    mock_load_template = AsyncMock(return_value="Test template content")
    mock_process_youtube_video = AsyncMock(return_value="Test YouTube transcript")
    mock_generate_content = AsyncMock(return_value="Test generated content")
    mock_save_generated_content = AsyncMock()

    template_hash = compute_template_hash("Test template content")

    class MockTranscription:
        def __init__(self, text):
            self.text = text

    with (
        patch("app.services.job.update_job_status", mock_update_job_status),
        patch("app.services.video_service.load_template", mock_load_template),
        patch("app.services.video_service.get_yt_video_id", return_value="test123"),
        patch("app.services.video_service.process_youtube_video", mock_process_youtube_video),
        patch(
            "app.services.video_service.generate_content_from_transcript",
            mock_generate_content,
        ),
        patch("app.services.video_service.save_generated_content", mock_save_generated_content),
        patch(
            "app.services.video_service.process_local_video",
            AsyncMock(return_value="Test Local Video Transcript"),
        ),
        patch("app.utils.cache_utils.settings.AUDIO_TRANSCRIPTION_MODEL", "test_model"),
        patch(
            "app.services.video_service.compute_file_hash",
            AsyncMock(return_value="test_file_hash"),
        ),
    ):
        input_data_youtube = MediaProcessingInput(
            url=AnyHttpUrl("https://www.youtube.com/watch?v=test123"),
            source=MediaSource.YOUTUBE,
            media_type=MediaType.VIDEO,
            template_id=1,
            user_id=1,
        )

        # Test with empty cache
        mock_redis.get.return_value = None
        result = await process_video(input_data_youtube, "test_job_id", mock_db)
        assert result["status"] == "success"
        mock_process_youtube_video.assert_called_once()
        mock_generate_content.assert_called_once()

        # Reset mock call counts
        mock_process_youtube_video.reset_mock()
        mock_generate_content.reset_mock()

        # Test with cached transcript
        mock_redis.get.side_effect = [json.dumps("Cached YouTube transcript"), None]
        result = await process_video(input_data_youtube, "test_job_id", mock_db)
        assert result["status"] == "success"
        mock_process_youtube_video.assert_not_called()  # Should not be called again
        mock_generate_content.assert_called_once()

        # Reset mock call counts
        mock_process_youtube_video.reset_mock()
        mock_generate_content.reset_mock()

        # Test with cached transcript and cached content
        mock_redis.get.side_effect = [
            json.dumps("Cached YouTube transcript"),
            json.dumps("Cached generated content"),
        ]
        result = await process_video(input_data_youtube, "test_job_id", mock_db)
        assert result["status"] == "success"
        mock_process_youtube_video.assert_not_called()  # Should not be called again
        mock_generate_content.assert_not_called()  # Should not be called again

        # Test local video processing
        input_data_local = MediaProcessingInput(
            file_path="/path/to/video.mp4",
            source=MediaSource.UPLOAD,
            media_type=MediaType.VIDEO,
            template_id=1,
            user_id=1,
        )

        # Test with empty cache for local video
        mock_redis.get.return_value = None
        mock_redis.set.reset_mock()  # Reset the mock to clear previous calls
        # Mock file hash computation to avoid FileNotFoundError
        with patch(
            "app.services.video_service.compute_file_hash",
            AsyncMock(return_value="test_local_file_hash"),
        ):
            result = await process_video(input_data_local, "test_job_id_local", mock_db)
        assert result["status"] == "success"

        # Check if transcription was cached
        expected_transcription = json.dumps({"text": "Test Local Video Transcript"})
        mock_redis.set.assert_any_call(
            cache_key_builder(
                "whisper_transcription",
                "test_local_file_hash",
                "test_model",
            ),
            expected_transcription,
            ex=604800,
        )

        # Check if generated content was cached
        # process_video defaults to 'gpt-4' if model_name is not specified
        # set_redis_data does json.dumps() on the value
        transcript_hash = compute_hash("Test Local Video Transcript")
        expected_content = json.dumps("Test generated content")
        # model_name defaults to 'gpt-4' when None or not set
        expected_key = cache_key_builder(
            "generated_content",
            transcript_hash,
            "1",
            template_hash,
            1,  # user_id (int, not string)
            "gpt-4",  # default model_name
        )
        mock_redis.set.assert_any_call(
            expected_key,
            expected_content,
            ex=86400,
        )

        mock_generate_content.assert_called_once()

        # Reset mock call counts
        mock_generate_content.reset_mock()
        mock_redis.set.reset_mock()

        # Test with cached transcription for local video
        mock_redis.get.side_effect = [
            json.dumps({"text": "Cached Local Video Transcript"}),
            None,  # Simulating no cached content
        ]
        # Mock file hash computation again
        with patch(
            "app.services.video_service.compute_file_hash",
            AsyncMock(return_value="test_local_file_hash"),
        ):
            result = await process_video(input_data_local, "test_job_id_local", mock_db)
        assert result["status"] == "success"
        mock_generate_content.assert_called_once()

        # Check if generated content was cached
        # process_video defaults to 'gpt-4' if model_name is not specified
        mock_redis.set.assert_called_with(
            cache_key_builder(
                "generated_content",
                compute_hash("Cached Local Video Transcript"),
                "1",
                template_hash,
                1,  # user_id
                "gpt-4",  # default model_name
            ),
            json.dumps("Test generated content"),
            ex=86400,
        )

        # Reset mock call counts
        mock_generate_content.reset_mock()
        mock_redis.set.reset_mock()

        # Test with both cached transcription and cached content for local video
        mock_redis.get.side_effect = [
            json.dumps("Cached Local Video Transcript"),
            json.dumps("Cached Generated Content"),
        ]
        # Mock file hash computation again
        with patch(
            "app.services.video_service.compute_file_hash",
            AsyncMock(return_value="test_local_file_hash"),
        ):
            result = await process_video(input_data_local, "test_job_id_local", mock_db)
        assert result["status"] == "success"
        mock_generate_content.assert_not_called()
        mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_compute_template_hash():
    template_content = "Test template content"
    expected_hash = hashlib.md5(template_content.encode("utf-8")).hexdigest()
    assert compute_template_hash(template_content) == expected_hash


@pytest.mark.asyncio
async def test_cache_expiration(mock_redis):
    key = "test_expiration_key"
    value = "test_value"
    expire_time = 1  # 1 second

    await set_cache(key, value, expire=expire_time)
    mock_redis.set.assert_called_once_with(key, json.dumps(value), ex=expire_time)

    # Simulate time passing
    mock_redis.get.return_value = None

    result = await get_cache(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_error_handling(mock_redis):
    mock_redis.set.side_effect = Exception("Redis connection error")
    mock_redis.get.side_effect = Exception("Redis connection error")

    key = "test_error_key"
    value = "test_value"

    # Test set_cache error handling
    result = await set_cache(key, value)
    assert result is False

    # Test get_cache error handling
    result = await get_cache(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_different_data_types(mock_redis):
    test_cases = [
        ("string_key", "string_value"),
        ("int_key", 42),
        ("float_key", 3.14),
        ("bool_key", True),
        ("list_key", [1, 2, 3]),
        ("dict_key", {"a": 1, "b": 2}),
    ]

    for key, value in test_cases:
        await set_cache(key, value)
        mock_redis.set.assert_called_once()

        # Check if the serialized value is correct
        call_args = mock_redis.set.call_args[0]
        assert call_args[0] == key
        assert json.loads(call_args[1]) == value
        assert mock_redis.set.call_args[1]["ex"] == 3600

        mock_redis.set.reset_mock()

        mock_redis.get.return_value = json.dumps(value)
        result = await get_cache(key)
        assert result is not None
        assert json.loads(result) == value


@pytest.mark.asyncio
async def test_cache_miss(mock_redis):
    mock_redis.get.return_value = None
    result = await get_cache("non_existent_key")
    assert result is None


@pytest.mark.asyncio
async def test_serialize_complex_object(mock_redis):
    class ComplexObject:
        def __init__(self, value):
            self.value = value

        def to_dict(self):
            return {"value": self.value}

        def __json__(self):
            return self.to_dict()

    complex_obj = ComplexObject("test")
    await set_cache("complex_key", complex_obj.to_dict())
    mock_redis.set.assert_called_once()

    call_args = mock_redis.set.call_args[0]
    assert call_args[0] == "complex_key"
    assert json.loads(call_args[1]) == {"value": "test"}
    assert mock_redis.set.call_args[1]["ex"] == 3600


@pytest.mark.asyncio
async def test_cache_invalidation(mock_redis):
    """Test cache invalidation functionality."""
    prefix = "test_prefix"
    args = ["arg1", "arg2"]

    # Reset the mock before the test
    mock_redis.delete.reset_mock()

    # Call invalidate_cache
    await invalidate_cache(prefix, *args)

    # Check if delete was called with the correct key
    expected_key = cache_key_builder(prefix, *args)
    mock_redis.delete.assert_called_once_with(expected_key)

    # Additional verification
    assert mock_redis.delete.call_count == 1, (
        f"Expected delete to be called once. Called {mock_redis.delete.call_count} times."
    )


if __name__ == "__main__":
    pytest.main(["-v", "test_caching.py"])
