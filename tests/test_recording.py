"""Unit tests for video recording functionality."""

import pytest
from selenium_mcp.tools.session import (
    _calculate_effective_recording,
    _merge_recording_capability,
)


class TestCalculateEffectiveRecording:
    """Tests for _calculate_effective_recording helper."""

    def test_force_overrides_client_request_true(self):
        """When force=True, should use default regardless of client (True case)."""
        # Client requests False, but force uses default (True)
        result = _calculate_effective_recording(
            record_video=False,
            recording_default=True,
            recording_force=True,
        )
        assert result is True

    def test_force_overrides_client_request_false(self):
        """When force=True, should use default regardless of client (False case)."""
        # Client requests True, but force uses default (False)
        result = _calculate_effective_recording(
            record_video=True,
            recording_default=False,
            recording_force=True,
        )
        assert result is False

    def test_client_request_true_respected_when_no_force(self):
        """When force=False, should use client's explicit True request."""
        result = _calculate_effective_recording(
            record_video=True,
            recording_default=False,
            recording_force=False,
        )
        assert result is True

    def test_client_request_false_respected_when_no_force(self):
        """When force=False, should use client's explicit False request."""
        result = _calculate_effective_recording(
            record_video=False,
            recording_default=True,
            recording_force=False,
        )
        assert result is False

    def test_default_used_when_client_not_specified_true(self):
        """When client is None, should use default (True case)."""
        result = _calculate_effective_recording(
            record_video=None,
            recording_default=True,
            recording_force=False,
        )
        assert result is True

    def test_default_used_when_client_not_specified_false(self):
        """When client is None, should use default (False case)."""
        result = _calculate_effective_recording(
            record_video=None,
            recording_default=False,
            recording_force=False,
        )
        assert result is False

    def test_force_with_none_client_uses_default(self):
        """When force=True and client is None, should use default."""
        result = _calculate_effective_recording(
            record_video=None,
            recording_default=True,
            recording_force=True,
        )
        assert result is True


class TestMergeRecordingCapability:
    """Tests for _merge_recording_capability helper."""

    def test_adds_capability_to_none(self):
        """Should add se:recordVideo when capabilities is None."""
        result = _merge_recording_capability(None, True)
        assert result == {"se:recordVideo": True}

    def test_adds_capability_to_empty_dict(self):
        """Should add se:recordVideo to empty capabilities."""
        result = _merge_recording_capability({}, True)
        assert result == {"se:recordVideo": True}

    def test_merges_with_existing_capabilities(self):
        """Should merge with existing capabilities."""
        existing = {"se:screenResolution": "1920x1080"}
        result = _merge_recording_capability(existing, True)
        assert result == {
            "se:screenResolution": "1920x1080",
            "se:recordVideo": True,
        }

    def test_does_not_mutate_original(self):
        """Should not mutate the original dict."""
        existing = {"se:screenResolution": "1920x1080"}
        result = _merge_recording_capability(existing, True)
        assert "se:recordVideo" not in existing
        assert "se:recordVideo" in result

    def test_record_video_false(self):
        """Should set se:recordVideo to False when record_video is False."""
        result = _merge_recording_capability(None, False)
        assert result == {"se:recordVideo": False}

    def test_overwrites_existing_record_video(self):
        """Should overwrite existing se:recordVideo capability."""
        existing = {"se:recordVideo": False}
        result = _merge_recording_capability(existing, True)
        assert result["se:recordVideo"] is True


class TestRecordingConfigIntegration:
    """Integration tests for recording configuration."""

    def test_config_recording_default_true_by_default(self):
        """Should default recording_default to True."""
        # Import fresh to test default
        from selenium_mcp.config import Settings
        settings = Settings()
        assert settings.recording_default is True

    def test_config_recording_force_false_by_default(self):
        """Should default recording_force to False."""
        from selenium_mcp.config import Settings
        settings = Settings()
        assert settings.recording_force is False
