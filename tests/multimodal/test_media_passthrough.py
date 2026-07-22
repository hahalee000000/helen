"""Tests for media() MediaPart passthrough and multi-arg form (Issue #17).

v1.25 fix: media() now accepts MediaPart objects (passthrough) and multiple
arguments (returns list[MediaPart]), aligning implementation with tutorial docs.
"""

import os
import tempfile

import pytest

from helen.runtime.media import MediaPart
from helen.stdlib.media import _media


def _make_png(path: str) -> str:
    """Create a minimal valid PNG file and return its path."""
    import base64
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
        "60e6kgAAAABJRU5ErkJggg=="
    )
    with open(path, "wb") as f:
        f.write(base64.b64decode(png_b64))
    return path


class TestMediaPassthrough:
    """Test media() MediaPart passthrough (single arg)."""

    def test_mediapart_passthrough_returns_same_object(self, tmp_path):
        """media(img) where img is MediaPart returns the same object."""
        png = _make_png(str(tmp_path / "test.png"))
        img = _media(png)
        assert isinstance(img, MediaPart)

        # passthrough: should return the exact same object
        result = _media(img)
        assert result is img
        assert isinstance(result, MediaPart)

    def test_mediapart_passthrough_preserves_fields(self, tmp_path):
        """Passthrough preserves all MediaPart fields."""
        png = _make_png(str(tmp_path / "test.png"))
        img = _media(png)

        result = _media(img)
        assert result.source == img.source
        assert result.content == img.content
        assert result.mime == img.mime
        assert result.media_type == img.media_type


class TestMediaMultiArg:
    """Test media() multi-argument form returning list[MediaPart]."""

    def test_multiple_mediaparts_return_list(self, tmp_path):
        """media(img1, img2) returns list[MediaPart]."""
        png = _make_png(str(tmp_path / "test.png"))
        img1 = _media(png)
        img2 = _media(png)

        result = _media(img1, img2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, MediaPart) for p in result)
        assert result[0] is img1
        assert result[1] is img2

    def test_multiple_strings_return_list(self, tmp_path):
        """media('a.png', 'b.png') returns list[MediaPart]."""
        png1 = _make_png(str(tmp_path / "a.png"))
        png2 = _make_png(str(tmp_path / "b.png"))

        result = _media(png1, png2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, MediaPart) for p in result)

    def test_mixed_string_and_mediapart_return_list(self, tmp_path):
        """media(img, 'path.png') returns list[MediaPart]."""
        png1 = _make_png(str(tmp_path / "a.png"))
        png2 = _make_png(str(tmp_path / "b.png"))
        img = _media(png1)

        result = _media(img, png2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is img
        assert isinstance(result[1], MediaPart)

    def test_three_args_return_list(self, tmp_path):
        """media(img1, img2, img3) returns list of 3."""
        png = _make_png(str(tmp_path / "test.png"))
        img1, img2, img3 = _media(png), _media(png), _media(png)

        result = _media(img1, img2, img3)
        assert isinstance(result, list)
        assert len(result) == 3


class TestMediaBackwardCompat:
    """Test backward compatibility with existing media() usage."""

    def test_single_string_returns_mediapart(self, tmp_path):
        """media('path.png') returns single MediaPart (not list)."""
        png = _make_png(str(tmp_path / "test.png"))
        result = _media(png)
        assert isinstance(result, MediaPart)
        assert not isinstance(result, list)

    def test_single_url_returns_mediapart(self):
        """media('https://...') returns single MediaPart."""
        result = _media("https://example.com/image.png")
        assert isinstance(result, MediaPart)
        assert result.source == "url"

    def test_keyword_media_type(self):
        """media('url', media_type='video') works with keyword arg."""
        result = _media("https://example.com/file.dat", media_type="video")
        assert isinstance(result, MediaPart)
        assert result.media_type == "video"

    def test_legacy_positional_type(self):
        """media('url', 'video') legacy positional type still works."""
        result = _media("https://example.com/file.dat", "video")
        assert isinstance(result, MediaPart)
        assert result.media_type == "video"

    def test_file_not_found_raises(self):
        """media('/nonexistent') raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            _media("/nonexistent/path/image.png")


class TestMediaErrorHandling:
    """Test media() error handling."""

    def test_no_args_raises(self):
        """media() with no args raises ValueError."""
        with pytest.raises(ValueError, match="at least one argument"):
            _media()

    def test_invalid_type_raises(self):
        """media(123) with non-str/non-MediaPart/non-list raises TypeError."""
        with pytest.raises(TypeError, match="must be str, MediaPart, or list"):
            _media(123)

    def test_invalid_type_in_multi_arg_raises(self):
        """media(img, 123) raises TypeError for invalid element."""
        png = _make_png("/tmp/test_media_err.png") if os.path.exists("/tmp") else None
        if png is None:
            pytest.skip("Cannot create temp file")
        img = _media(png)
        with pytest.raises(TypeError, match="must be str, MediaPart, or list"):
            _media(img, 123)


class TestMediaLlmActIntegration:
    """Test that media(img1, img2) flattens correctly in llm act context.

    These tests verify the interpreter's media expression evaluation and
    list-flattening logic (llm_mixin.py) without making real LLM calls.
    """

    def test_media_list_flattens_in_llm_act(self, tmp_path):
        """media(img1, img2) in llm act produces 2 media_parts (not 1 list)."""
        # This is an integration test: we verify the flattening logic by
        # checking that a list result is expanded into individual MediaParts.
        png = _make_png(str(tmp_path / "test.png"))
        img1 = _media(png)
        img2 = _media(png)

        # Simulate what llm_mixin does: evaluate media expr -> list -> flatten
        media_val = _media(img1, img2)
        assert isinstance(media_val, list)

        media_parts = []
        if isinstance(media_val, MediaPart):
            media_parts.append(media_val)
        elif isinstance(media_val, list):
            for item in media_val:
                if isinstance(item, MediaPart):
                    media_parts.append(item)

        assert len(media_parts) == 2
        assert media_parts[0] is img1
        assert media_parts[1] is img2


class TestMediaListFlattening:
    """Test media(list) dynamic list flattening (no spread syntax needed).

    v1.25.1: media() accepts a single list argument and flattens it into
    list[MediaPart], enabling llm act "..." media(images) for dynamic lists.
    """

    def test_single_list_of_mediaparts_flattens(self, tmp_path):
        """media([img1, img2]) returns list[MediaPart] (flattened)."""
        png = _make_png(str(tmp_path / "test.png"))
        img1, img2 = _media(png), _media(png)

        result = _media([img1, img2])
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is img1
        assert result[1] is img2

    def test_single_list_of_strings_flattens(self, tmp_path):
        """media(['a.png', 'b.png']) returns list[MediaPart]."""
        png1 = _make_png(str(tmp_path / "a.png"))
        png2 = _make_png(str(tmp_path / "b.png"))

        result = _media([png1, png2])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, MediaPart) for p in result)

    def test_single_mixed_list_flattens(self, tmp_path):
        """media([img, 'path.png']) returns list[MediaPart]."""
        png1 = _make_png(str(tmp_path / "a.png"))
        png2 = _make_png(str(tmp_path / "b.png"))
        img = _media(png1)

        result = _media([img, png2])
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is img
        assert isinstance(result[1], MediaPart)

    def test_empty_list_returns_empty_list(self):
        """media([]) returns empty list (no media)."""
        result = _media([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_element_list_flattens_to_list(self, tmp_path):
        """media([img]) returns list[MediaPart] with 1 element (not unwrapped)."""
        png = _make_png(str(tmp_path / "test.png"))
        img = _media(png)

        result = _media([img])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] is img

    def test_list_in_multi_arg_flattens(self, tmp_path):
        """media(img, [img2, img3]) flattens nested list in multi-arg."""
        png = _make_png(str(tmp_path / "test.png"))
        img1, img2, img3 = _media(png), _media(png), _media(png)

        result = _media(img1, [img2, img3])
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] is img1
        assert result[1] is img2
        assert result[2] is img3

    def test_list_with_invalid_item_raises(self):
        """media([123]) raises TypeError for invalid item."""
        with pytest.raises(TypeError, match="list item must be str or MediaPart"):
            _media([123])

    def test_dynamic_list_flatten_in_llm_act_context(self, tmp_path):
        """media(images) dynamic list produces N media_parts in llm act."""
        png = _make_png(str(tmp_path / "test.png"))
        images = [_media(png), _media(png), _media(png)]

        # Simulate llm_mixin flattening for media(images)
        media_val = _media(images)
        assert isinstance(media_val, list)

        media_parts = []
        if isinstance(media_val, MediaPart):
            media_parts.append(media_val)
        elif isinstance(media_val, list):
            for item in media_val:
                if isinstance(item, MediaPart):
                    media_parts.append(item)

        assert len(media_parts) == 3


class TestMediaReadOnlyView:
    """Test media() accepts ReadOnlyView (agent parameters) -- Issue #18.

    v1.25.2: Agent parameters wrapping a list are ReadOnlyView, not list.
    media() now flattens list-backed ReadOnlyView so dynamic media lists
    work inside agent main {}.
    """

    def _make_rov(self, items):
        """Create a list-backed ReadOnlyView (simulates agent parameter)."""
        from helen.interpreter.readonly_view import ReadOnlyView
        return ReadOnlyView(list(items))

    def test_single_readonlyview_of_mediaparts_flattens(self, tmp_path):
        """media(ReadOnlyView[img1, img2]) returns list[MediaPart]."""
        png = _make_png(str(tmp_path / "test.png"))
        img1, img2 = _media(png), _media(png)
        rov = self._make_rov([img1, img2])

        result = _media(rov)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is img1
        assert result[1] is img2

    def test_single_readonlyview_of_strings_flattens(self, tmp_path):
        """media(ReadOnlyView['a.png', 'b.png']) returns list[MediaPart]."""
        png1 = _make_png(str(tmp_path / "a.png"))
        png2 = _make_png(str(tmp_path / "b.png"))
        rov = self._make_rov([png1, png2])

        result = _media(rov)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(p, MediaPart) for p in result)

    def test_readonlyview_in_multi_arg_flattens(self, tmp_path):
        """media(img, ReadOnlyView[img2, img3]) flattens nested ROV."""
        png = _make_png(str(tmp_path / "test.png"))
        img1, img2, img3 = _media(png), _media(png), _media(png)
        rov = self._make_rov([img2, img3])

        result = _media(img1, rov)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] is img1
        assert result[1] is img2
        assert result[2] is img3

    def test_empty_readonlyview_returns_empty_list(self):
        """media(ReadOnlyView[]) returns empty list."""
        rov = self._make_rov([])
        result = _media(rov)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_dict_backed_readonlyview_not_treated_as_list(self):
        """media(ReadOnlyView{dict}) raises TypeError (not flattened)."""
        from helen.interpreter.readonly_view import ReadOnlyView
        rov = ReadOnlyView({"a": 1, "b": 2})  # dict-backed

        with pytest.raises(TypeError, match="must be str, MediaPart, or list"):
            _media(rov)

    def test_readonlyview_flatten_in_llm_act_context(self, tmp_path):
        """media(rov) dynamic list produces N media_parts in llm act."""
        png = _make_png(str(tmp_path / "test.png"))
        images = [_media(png), _media(png), _media(png)]
        rov = self._make_rov(images)

        media_val = _media(rov)
        assert isinstance(media_val, list)

        media_parts = []
        if isinstance(media_val, MediaPart):
            media_parts.append(media_val)
        elif isinstance(media_val, list):
            for item in media_val:
                if isinstance(item, MediaPart):
                    media_parts.append(item)

        assert len(media_parts) == 3
