# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.48"]
# ///
"""Render ai-brain-architecture.html to an animated GIF.

    uv run --script docs/architecture/render.py

Needs ffmpeg and a Playwright Chromium (`uvx playwright install chromium`),
or pass --chrome /path/to/chrome. If gifsicle is on PATH (or passed with
--gifsicle, e.g. from `npx gifsicle`), the GIF is also lossily compressed.
"""

import argparse
import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--width", type=int, default=1280, help="GIF width; the canvas is 1280x720")
    ap.add_argument("--colors", type=int, default=128)
    ap.add_argument("--chrome", help="Chrome or Chromium executable to use instead of Playwright's")
    ap.add_argument("--gifsicle", default=shutil.which("gifsicle"), help="gifsicle executable for the final pass")
    ap.add_argument("--lossy", type=int, default=30, help="gifsicle --lossy level")
    ap.add_argument("--out", type=Path, default=HERE / "ai-brain-architecture.gif")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chrome)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto((HERE / "ai-brain-architecture.html").as_uri() + "?render=1")
        page.evaluate("document.fonts.ready")
        duration = page.evaluate("window.DURATION")
        frames = round(duration * args.fps)
        for i in range(frames):
            data = page.evaluate("t => window.frame(t)", i / args.fps)
            Path(tmp, f"f{i:04d}.png").write_bytes(base64.b64decode(data.split(",", 1)[1]))
        browser.close()

        scale = f"scale={args.width}:-1:flags=lanczos," if args.width != 1280 else ""
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", f"{tmp}/f%04d.png",
                "-filter_complex",
                f"[0:v]{scale}split[a][b];[a]palettegen=max_colors={args.colors}:stats_mode=full[p];"
                "[b][p]paletteuse=dither=none:diff_mode=rectangle",
                "-loop", "0", str(args.out),
            ],
            check=True,
        )
    if args.gifsicle:
        subprocess.run([args.gifsicle, "-O3", f"--lossy={args.lossy}", "-b", str(args.out)], check=True)
    print(f"{args.out} ({frames} frames, {args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
