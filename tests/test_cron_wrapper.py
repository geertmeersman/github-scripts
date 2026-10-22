import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "container"))

import cron_wrapper


class TestAppendRunHistory:
    def test_creates_history_file_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            with (
                patch.object(cron_wrapper, "HISTORY_FILE", str(history_file)),
                patch.object(cron_wrapper, "LOG_DIR", tmpdir),
            ):
                cron_wrapper.append_run_history(
                    "test",
                    "success",
                    "2024-01-01_00-00-00",
                    "2024-01-01_00-00-01",
                    1.0,
                    "test.log",
                )
            data = json.loads(history_file.read_text())
            assert len(data) == 1
            assert data[0]["script"] == "test"
            assert data[0]["status"] == "success"

    def test_appends_to_existing_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history_file.write_text('[{"script": "existing", "status": "success"}]')
            with (
                patch.object(cron_wrapper, "HISTORY_FILE", str(history_file)),
                patch.object(cron_wrapper, "LOG_DIR", tmpdir),
            ):
                cron_wrapper.append_run_history(
                    "new",
                    "error",
                    "2024-01-01_00-00-00",
                    "2024-01-01_00-00-01",
                    1.0,
                    "new.log",
                )
            data = json.loads(history_file.read_text())
            assert len(data) == 2
            assert data[1]["script"] == "new"

    def test_handles_corrupt_history_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history_file.write_text("not valid json")
            with (
                patch.object(cron_wrapper, "HISTORY_FILE", str(history_file)),
                patch.object(cron_wrapper, "LOG_DIR", tmpdir),
            ):
                cron_wrapper.append_run_history(
                    "test",
                    "success",
                    "2024-01-01_00-00-00",
                    "2024-01-01_00-00-01",
                    1.0,
                    "test.log",
                )
            data = json.loads(history_file.read_text())
            assert len(data) == 1
