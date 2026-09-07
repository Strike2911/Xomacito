"""Image preview / output pairing regression tests without network or AI models."""
from pathlib import Path
from unittest.mock import Mock

from PIL import Image
from PySide6.QtCore import QUrl

from src.ui.image_controller import ImageController

ROOT = Path(__file__).resolve().parents[1]

class Store:
    def __init__(self, output):
        self.values = {"image_output_path": str(output)}
    def get(self, key, default=None):
        return self.values.get(key, default)
    def set(self, key, value):
        self.values[key] = value

def make(tmp_path):
    return ImageController(ROOT, Store(tmp_path), Mock(), "1.1")

def item(key, path, title="same"):
    return {"itemId": key, "path": str(path), "title": title, "page": 1, "mediaType": "image", "output": ""}

def test_raster_preview_does_not_load_ai_and_preserves_alpha(tmp_path):
    controller = make(tmp_path)
    source = ROOT / "assets/progress/cat-run-1.png"
    controller._ensure_engines = Mock(side_effect=AssertionError("Raster preview loaded AI"))
    result = controller._thumbnail_worker(item("one", source))
    with Image.open(result["path"]) as preview:
        assert preview.mode == "RGBA"
        assert max(preview.size) <= 900
        assert preview.getchannel("A").getextrema()[0] == 0
    controller._ensure_engines.assert_not_called()
    Path(result["path"]).unlink()

def test_outputs_with_same_title_are_paired_by_id(tmp_path):
    controller = make(tmp_path)
    first = tmp_path / "same.png"
    second = tmp_path / "same_1.png"
    first.touch()
    second.touch()
    controller.items.replace([item("one", first), item("two", second)])
    controller._set_state(selectedIndex=1, busy=True)
    controller._process_item_outputs = {"one": str(first), "two": str(second)}
    controller._process_done([str(first), str(second)])
    assert controller.items.item(0)["output"] == str(first)
    assert controller.items.item(1)["output"] == str(second)
    assert controller.pool.submit.call_args.args[1]["path"] == str(second)
    controller.pool.submit.call_args.kwargs["on_result"]({"path": str(second)})
    assert controller.state["resultPreviewSource"] == QUrl.fromLocalFile(str(second)).toString()

def test_late_preview_from_removed_or_unselected_item_cannot_replace_comparison(tmp_path):
    controller = make(tmp_path)
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    controller.items.replace([{**item("b", b), "output": str(b)}])
    controller._set_state(selectedIndex=0, previewSource="current", resultPreviewSource="current-result")
    controller._thumbnail_done(0, {"path": str(a)}, "a")
    controller._selected_result_done("a", str(a), {"path": str(a)})
    assert controller.state["previewSource"] == "current"
    assert controller.state["resultPreviewSource"] == "current-result"

def test_running_job_keeps_inputs_stable_and_reserves_100_for_completion(tmp_path):
    controller = make(tmp_path)
    controller.items.replace([item("a", tmp_path / "a.png")])
    controller._set_state(selectedIndex=0, busy=True)
    controller._apply_progress(1.0, "Finalizando")
    assert controller.state["progress"] == 0.99
    controller.setTask("convert")
    controller.remove(0)
    assert controller.state["task"] == "removeBackground"
    assert controller.items.rowCount() == 1
    controller._set_state(busy=False, progress=1.0)
    controller._apply_progress(0.3, "Late callback")
    assert controller.state["progress"] == 1.0
