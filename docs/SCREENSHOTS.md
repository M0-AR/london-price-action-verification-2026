# Screenshots — regenerating `assets/screenshot-preview.png`

`preview.html` is a single self-contained file (no build step, no CDN
required). The screenshot is taken locally with a real browser so what you
see in the README is what visitors get on GitHub Pages.

## Regenerate (copy-paste)

```bash
python3 -m http.server 8000 --directory /home/md/src/hussein-london-price-action-verification-2026 &
# then with Playwright (python or node), or manually:
# open http://localhost:8000/preview.html → screenshot 1280x900 → save assets/screenshot-preview.png
```

## What to capture

- Full hero + CEO summary + first chart (1280×900 viewport).
- Keep the file < 1 MB (`pngquant` or `cjpeg` if needed).
- Commit the PNG next to the README change so they never drift apart.
