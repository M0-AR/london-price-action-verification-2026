# Demo video / GIF — how to record and embed

GitHub renders animated GIFs everywhere Markdown renders (repo page, mobile,
npm/PyPI mirrors). It strips raw `<video>` tags, so use these two supported
patterns (2026 best practice):

## Option A — GIF (recommended, autoplay everywhere)

1. Record 15–30s, 800px wide max, 10–15 fps (keeps file < 10 MB).
   - Linux: `peek` or `byzanz`, or terminal: `screencli`
   - Mac: QuickTime screen recording → convert: `ffmpeg -i in.mov -vf "fps=12,scale=800:-1" -gifflags +transdiff out.gif`
   - Windows: ScreenToGif.
2. Save as `assets/demo.gif` (keep under ~10 MB so the README loads fast).
3. Embed at the top of `README.md`:
   ```markdown
   ![Demo — 30s end-to-end run](assets/demo.gif)
   ```

Suggested GIF script (this repo):
`docker compose up --build` → show `results/*.json` appearing →
open `preview.html` → answer 3 quiz questions.

## Option B — Video with thumbnail (YouTube, with sound)

1. Upload to YouTube (unlisted is fine).
2. In `README.md` use a clickable thumbnail (opens YouTube, plays with sound):
   ```markdown
   [![Watch the 2-min demo](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)
   ```
   Replace `YOUR_VIDEO_ID` with the real ID.

## Screenshots

`assets/screenshot-preview.png` in this repo is generated automatically from
`preview.html` (see `docs/SCREENSHOTS.md`). Re-generate after any
`preview.html` change so the README visual never goes stale.
