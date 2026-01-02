
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from tatlam.cli.render_cards import (
    _json_to_list,
    _none_if_blank,
    coerce_row_types,
    safe_filename,
    unique_path,
    render_html,
    main,
    fetch
)

class TestRenderCards:

    def test_json_to_list(self):
        assert _json_to_list(None) == []
        assert _json_to_list([]) == []
        assert _json_to_list(["a"]) == ["a"]
        assert _json_to_list("[]") == []
        assert _json_to_list('["a"]') == ["a"]
        assert _json_to_list('{"a":1}') == [{"a":1}] # Wrapped
        assert _json_to_list("not json") == ["not json"]

    def test_none_if_blank(self):
        assert _none_if_blank(None) is None
        assert _none_if_blank("") is None
        assert _none_if_blank("   ") is None
        assert _none_if_blank(" a ") == "a"

    def test_coerce_row_types(self):
        row = {
            "title": "Title",
            "steps": '["s1"]',
            "mask_usage": "Yes"
        }
        res = coerce_row_types(row)
        assert res["steps"] == ["s1"]
        assert res["mask_usage"] == "כן"
        assert res["location"] == ""

    def test_coerce_row_types_defaults(self):
        row = {}
        res = coerce_row_types(row)
        assert res["title"] == "ללא כותרת"
        assert res["steps"] == []

    def test_safe_filename(self):
        assert safe_filename("שם קובץ") == "שם_קובץ"
        assert safe_filename("file/name.txt") == "file-name.txt"
        assert safe_filename("  test  ") == "test"

    def test_unique_path(self, tmp_path):
        f1 = tmp_path / "test.txt"
        f1.touch()
        
        p = unique_path(tmp_path, "test.txt")
        assert p.name == "test-1.txt"
        assert p.parent == tmp_path
        
        p2 = unique_path(tmp_path, "other.txt")
        assert p2.name == "other.txt"

    def test_render_html(self):
        scenarios = [
            {"title": "T1", "steps": ["s1"]},
            {}
        ]
        html = render_html(scenarios)
        assert "<html" in html
        assert "T1" in html
        assert "ללא כותרת" in html
        assert "<li>s1</li>" in html

    def test_render_html_empty(self):
        assert "אין תרחישים" in render_html([])

    @patch("tatlam.cli.render_cards.get_session")
    def test_fetch(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock scalars result
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": 1}
        mock_session.scalars.return_value.all.return_value = [mock_obj]
        
        res = fetch(category="C", bundle_id="B")
        assert len(res) == 1
        assert res[0]["id"] == 1
        mock_session.scalars.assert_called()

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main(self, mock_load_tpl, mock_fetch, tmp_path):
        mock_fetch.return_value = [{"title": "T1", "id": 1}]
        mock_tpl = MagicMock()
        mock_tpl.render.return_value = "content"
        mock_load_tpl.return_value = mock_tpl
        
        out_dir = tmp_path / "out"
        
        # Test basic run
        args = ["--out", str(out_dir), "--prefix-id"]
        ret = main(args)
        assert ret == 0
        assert (out_dir / "1_T1.md").exists()
        
        # Test subdirs
        args = ["--out", str(out_dir), "--subdirs-by-category"]
        main(args)
