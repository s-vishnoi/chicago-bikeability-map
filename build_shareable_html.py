from pathlib import Path
import base64
import re


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "chicago-bikeability-atlas.html"


def escape_inline_css(text: str) -> str:
    return text.replace("</style>", "<\\/style>")


def escape_inline_js(text: str) -> str:
    return (
        text.replace("</script>", "<\\/script>")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def escape_inline_json(text: str) -> str:
    return (
        text.replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_shareable_html() -> Path:
    index_html = (ROOT / "index.html").read_text()
    styles = escape_inline_css((ROOT / "styles.css").read_text())
    script = escape_inline_js((ROOT / "app.js").read_text())
    atlas_data = escape_inline_json((ROOT / "data" / "atlas-data.json").read_text())
    
    if (ROOT / "bike_cursor.png").exists():
        cursor_b64 = base64.b64encode((ROOT / "bike_cursor.png").read_bytes()).decode("ascii")
        index_html = index_html.replace(
            'src="bike_cursor.png"',
            f'src="data:image/png;base64,{cursor_b64}"'
        )
        index_html = index_html.replace(
            'href="bike_cursor.png"',
            f'href="data:image/png;base64,{cursor_b64}"'
        )
        
    if (ROOT / "chicago_background.webp").exists():
        bg_b64 = base64.b64encode((ROOT / "chicago_background.webp").read_bytes()).decode("ascii")
        styles = styles.replace(
            'url("chicago_background.webp")',
            f'url("data:image/webp;base64,{bg_b64}")'
        )

    if (ROOT / "chicago_city_timelapse.gif").exists():
        timelapse_b64 = base64.b64encode((ROOT / "chicago_city_timelapse.gif").read_bytes()).decode("ascii")
        styles = styles.replace(
            'url("chicago_city_timelapse.gif")',
            f'url("data:image/gif;base64,{timelapse_b64}")'
        )
        
    if (ROOT / "bikeability_score_help.webp").exists():
        help_b64 = base64.b64encode((ROOT / "bikeability_score_help.webp").read_bytes()).decode("ascii")
        index_html = index_html.replace(
            'src="bikeability_score_help.webp"',
            f'src="data:image/webp;base64,{help_b64}"'
        )

    index_html = index_html.replace(
        '<link rel="stylesheet" href="styles.css" />',
        f"<style>\n{styles}\n    </style>",
    )
    inline_bundle = (
        "    <script id=\"atlas-data\" type=\"application/json\">\n"
        f"{atlas_data}\n"
        "    </script>\n"
        "    <script>\n"
        f"{script}\n"
        "    </script>"
    )
    index_html, count = re.subn(
        r'<script src="app\.js(\?v=[^"]+)?"></script>',
        lambda _: inline_bundle,
        index_html,
        count=1,
    )
    if not count:
        raise RuntimeError("Could not find the app.js script tag in index.html")

    OUTPUT.write_text(index_html)
    return OUTPUT


if __name__ == "__main__":
    output = build_shareable_html()
    print(f"Wrote {output}")
