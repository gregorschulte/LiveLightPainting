# LiveLightPainting

Interactive light-painting art installation. A webcam watches a dark room,
visitors draw with light objects, and the painting builds up live on screen.
Each round runs for a configurable interval (default 30 s, shown as a progress
bar at the bottom edge), the finished painting is then held on screen
(default 10 s) and saved to disk — then the next round starts automatically.

The long exposure is emulated digitally: bright pixels of each frame are merged
into an accumulator (running maximum), so light "burns into" the image while
the dark room stays dark. A brightness threshold suppresses sensor noise and
ambient light.

## Installation (Windows & Linux)

```bash
pip install -r requirements.txt
```

Linux only: your user must be able to access the webcam, e.g. be in the
`video` group (`sudo usermod -aG video $USER`, then re-login).

## Usage

```bash
python main.py              # run with webcam
python main.py --demo       # synthetic moving light, no webcam needed
python main.py --fullscreen # start in fullscreen (exhibition mode)
```

### Hotkeys

| Key     | Action                     |
|---------|----------------------------|
| `S`     | Open settings dialog       |
| `F`     | Toggle fullscreen          |
| `Space` | Discard and restart round  |
| `Esc`   | Quit                       |

### Settings (persisted to `settings.json`)

- **Webcam** – select among detected cameras
- **Framerate** – requested capture rate
- **Exposure** – auto on/off + manual value. *Note:* the meaning of the raw
  value depends on the driver (Windows/DirectShow: log2 of seconds, e.g. `-6`
  = 1/64 s; Linux/V4L2: driver specific). A very long exposure lowers the
  effective framerate.
- **Recording interval** – painting time per round (default 30 s)
- **Hold interval** – how long the finished painting is shown (default 10 s)
- **Brightness threshold** – minimum brightness (0–255) a pixel needs to be
  recorded; raise it in brighter rooms so only real light objects draw
- **Blend mode** – `maximum` (classic long exposure), `add` (brighter, more
  saturated trails), `screen`
- **Mirror** – horizontal flip, natural for visitors facing the camera
- **Save** – save each finished painting as a timestamped PNG in the chosen
  folder (default `paintings/`)

## Development

Headless smoke test (engine + full GUI pipeline in demo mode, no webcam or
display needed):

```bash
python smoke_test.py
```

## Project layout

```
main.py                  entry point
app/settings.py          settings dataclass + JSON persistence
app/painting_engine.py   light accumulation + round state machine
app/camera_worker.py     capture thread (+ demo source), camera enumeration
app/main_window.py       live view, progress bar, hotkeys, saving
app/settings_dialog.py   settings UI
paintings/               saved results
```

