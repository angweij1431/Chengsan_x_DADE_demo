# Instructions: Run the Booth and Generate a Dance Video from the UI

## 1. Start the server

From the project root, with your virtual environment already set up and `.env` configured (`MINIMAX_API_KEY` set, `DANCE_PROVIDER=minimax`):

```
.venv\Scripts\python.exe booth_app.py
```

The console prints a startup banner confirming the dance provider, the MiniMax video model in use, and whether `MINIMAX_API_KEY` was accepted. Fix anything flagged there before continuing — a rejected key will fail every generation.

## 2. Open the booth in a browser

- On the same machine: **http://localhost:5000**
- On a phone on the same Wi-Fi: use the "Phones:" address printed in the startup banner

## 3. Pick the dance station

On the home screen, click **"Make me dance"**.

## 4. Upload your photo

Click the **"Your photo"** slot (📷) and select an image of yourself. This is the photo MiniMax uses as the first frame of the video.

## 5. Choose how the dance is driven

You have two options, and they're mutually exclusive — the custom clip wins if both are filled in:

- **Pick a built-in style** — click one of the chips under "Choose a dance" (e.g. Chill Groove, Ballroom Waltz, K-Pop Idol, Runway Pose, or any custom template you've added to `TEMPLATES` in `booth/video_dance.py`, such as `my_template`).
- **Or upload your own dance clip** — click the **"Your own dance clip"** slot (🖼️) and select a short video of yourself or someone else dancing. The app extracts frames with ffmpeg, has MiniMax's vision model describe the moves in words, and uses that description to drive the generation. This costs one extra (small) billed API call on top of the video generation.

## 6. Generate

Click **Generate**. The app switches to a "Working on it…" screen — MiniMax video generation typically takes 1–5 minutes, not the ~10–30 seconds the placeholder text suggests.

## 7. Get your video

Once done, the result screen shows:
- The generated video, playable inline
- A **QR code** to scan and save it to a phone
- A **Download** button
- Options to try again or return to the station picker

Downloaded/generated files are also saved locally under `outputs/`.

## Notes

- Every dance generation is a **real, billed MiniMax API call** (see `DANCE_PROVIDER=minimax` in `.env`). There is no free tier.
- If you don't want to spend money while testing the UI flow, set `DANCE_PROVIDER=mock` in `.env` and restart the server — this renders a local placeholder video (a Ken Burns zoom on your photo) with no API calls.
- Rate limits (`LIMIT_DANCE_TEMPLATE_SESSION`, `LIMIT_DANCE_CUSTOM_SESSION`, etc. in `.env`) cap how many generations one browser session/day can do — relevant if testing repeatedly.
