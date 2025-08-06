# 👾 plansi

pipeline for text; a video player, cast quantizer, saver of scrollbacks

## ▶ Usage

```bash
# play to terminal
uvx plansi video.mp4

# write to asciinema file
uvx plansi video.mp4 video.cast

# with options
uvx plansi video.mp4 --fps=15 --threshold=10 --debug
uvx plansi video.mp4 --cache-position --no-cache-style
```

## TODO - Version 0.1.0

### 🗑️ refactor

- [ ] fix dogshit cli
- [x] make nice and pipeliney
- [x] get some logging in 🪵
- [ ] write some tests
  - [ ] write some integration tests
- [ ] performance tuning
- [ ] write some docs

### 🌐 Streaming & Input Sources
- [ ] **yt-dlp integration**: Auto-detect `http://`/`https://` URLs and use yt-dlp API to get direct streaming URLs
- [ ] **Fallback strategy**: Try ffmpeg first, fall back to yt-dlp if that fails
- [ ] **Webcam support**: Add `--camera` flag to treat input as webcam device
  - [ ] Linux: `/dev/video0` with v4l2
  - [ ] Windows: DirectShow device enumeration
  - [ ] macOS: AVFoundation device support

### 📺 Terminal & Display
- [ ] **SIGWINCH handling**: Resize video on terminal window resize during live playback
- [ ] **Cast file quantization**: Quantize existing .cast files

### 🔧 API Improvements
- [ ] **File-like object support**: Allow writing to BytesIO, StringIO for textual-asciinema
