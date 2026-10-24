"""Regression tests for the Graphviz-free fallback SVG (issue #179)."""


class _FakeAnalyzer:
    def __init__(self, graph, root):
        self.graph = graph
        self.root = root


def test_fallback_svg_escapes_xml_sensitive_filenames(tmp_path, monkeypatch):
    import pathlib
    import subprocess
    import xml.etree.ElementTree as ET
    from peek.graph import build_svg

    # build_svg only consumes the analyzer's paths, so no files need to exist:
    # Windows forbids creating names containing < or > (issue #179).
    ar = _FakeAnalyzer(
        {
            pathlib.Path(tmp_path / "a&b.py"): {
                pathlib.Path(tmp_path / "a<b.py"),
                pathlib.Path(tmp_path / "a>b.py"),
            }
        },
        tmp_path,
    )

    def _no_graphviz(*args, **kwargs):
        raise FileNotFoundError("dot")

    # build_svg() imports subprocess inside the try block; patch the real module
    monkeypatch.setattr(subprocess, "check_output", _no_graphviz)

    svg = build_svg(ar)
    ET.fromstring(svg)  # well-formed XML: no raw & < > inside the text element
    assert "a&amp;b.py" in svg
    assert "a&lt;b.py" in svg
    assert "a&gt;b.py" in svg


def test_graphviz_success_path_preserved(tmp_path, monkeypatch):
    import pathlib
    import subprocess
    from peek.graph import build_svg

    f = tmp_path / "a.py"
    f.write_text("x=1\n", encoding="utf-8")
    ar = _FakeAnalyzer({pathlib.Path(f): set()}, tmp_path)

    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: b"<svg>real graphviz output</svg>",
    )

    assert "real graphviz output" in build_svg(ar)


def test_fallback_keeps_size_limit(tmp_path, monkeypatch):
    import pathlib
    import subprocess
    import xml.etree.ElementTree as ET
    from peek.graph import build_dot, build_svg

    # a wide graph whose DOT text exceeds the 200-character display window
    graph = {}
    for i in range(20):
        graph[pathlib.Path(tmp_path / f"file_{i:02d}.py")] = {
            pathlib.Path(tmp_path / f"dep_{i:02d}.py")
        }
    ar = _FakeAnalyzer(graph, tmp_path)

    monkeypatch.setattr(
        subprocess, "check_output", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("dot"))
    )

    svg = build_svg(ar)
    text_el = ET.fromstring(svg).find("{http://www.w3.org/2000/svg}text")
    assert text_el is not None
    assert text_el.text == build_dot(ar)[:200]
