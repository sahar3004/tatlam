from unittest.mock import MagicMock, patch
import json
from tatlam.cli.export_json import main, fetch_rows, normalize


class TestExportJSON:

    @patch("tatlam.cli.export_json.get_session")
    def test_fetch_rows_logic(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": 1, "title": "T"}
        mock_session.scalars.return_value.all.return_value = [mock_obj]

        rows = fetch_rows(category="C")
        assert len(rows) == 1
        assert rows[0]["id"] == 1

        rows2 = fetch_rows(bundle_id="B")
        assert len(rows2) == 1

    def test_normalize(self):
        row = {"steps": '["s1"]', "other": "val"}
        # Assuming to_dict already parses, but normalize handles raw strings if any
        res = normalize(row)
        assert res["steps"] == ["s1"]
        assert res["other"] == "val"

        # Test invalid json fallback
        row_bad = {"steps": "invalid"}
        res_bad = normalize(row_bad)
        assert res_bad["steps"] == []

    @patch("tatlam.cli.export_json.get_session")
    def test_main(self, mock_get_session, tmp_path):
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": 1, "title": "T", "steps": []}
        mock_session.scalars.return_value.all.return_value = [mock_obj]

        out_file = tmp_path / "scenarios.json"

        args = ["--out", str(out_file), "--category", "C"]

        ret = main(args)
        assert ret == 0

        with open(out_file) as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["id"] == 1
