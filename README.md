# Chengsan × DADE — Interactive Booth

A three-station photo/video booth for community events. Visitors upload a photo
and walk away with something they can scan and take home.

| # | Station | Visitor gives | Gets back | Model | Cost |
|---|---------|---------------|-----------|-------|------|
| 1 | **Make me dance** | A photo, plus either a built-in dance template **or** their own dance clip | A dance video of themselves | MiniMax Hailuo 2.3 (image-to-video) | 💳 **PAID** |
| 2 | **Edit my photo** | Their photo + a reference photo | An edited image | MiniMax `image-01` + `MiniMax-M3` vision | 💳 **PAID** |
| 3 | **Put me somewhere** | Their photo + an environment photo | Them composited into that place | MiniMax `image-01` + `MiniMax-M3` vision | 💳 **PAID** |

Every result is written to `outputs/` and offered as a QR code pointing at the
booth laptop's LAN address, so a visitor scans and downloads to their phone.

**The whole booth runs on one MiniMax API key.** There is no Google, Gemini or
Vertex dependency anywhere in the booth code.

---

## Legend used throughout this document

| Marker | Meaning |
|--------|---------|
| 💳 **PAID** | Costs real money per use. |
| 🆓 | Costs nothing. |
| ✏️ **YOU ENTER** | A value only you can supply — a key, a URL, a host. Nothing works until you fill it in. |
| ⚠️ | A trap that will bite you at the event if you skip it. |

---

# Part 1 — Quick start

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
cp .env.example .env                # then edit .env — see the next section
python booth_app.py
```

Open <http://localhost:5000>.

Install [ffmpeg](https://ffmpeg.org/download.html) and put it on your PATH too.
It is not optional for both halves of the booth:

- Without it, the offline `mock` renderer produces a still image instead of a
  video.
- Without it, the **"bring your own dance clip"** path fails outright — ffmpeg
  is how the clip is read at all (see Part 4).

Check your key before anything else:

```bash
python -m booth.minimax_image     # prints the models in use and validates the key
```

---

# Part 2 — ✏️ Everything YOU have to enter

These are the only values that are not already filled in. Everything else in
`.env.example` has a working default.

### Required — the booth will not start without this

| Variable | Where to get it | Notes |
|----------|-----------------|-------|
| `MINIMAX_API_KEY` | <https://platform.minimax.io/user-center/basic-information> | ✏️ **YOU ENTER.** One key powers all three stations. 💳 There is no free tier — see Part 3. |

⚠️ **Region matters, and it is not a setting you can get away with guessing.**
`api.minimax.io` is the international platform. The mainland China platform is a
different host **and a separate account/key namespace** — a key from one will
not authenticate against the other. If you signed up in mainland China, set
`MINIMAX_API_BASE=https://api.minimaxi.com`. A wrong region looks exactly like a
wrong key (MiniMax code `1004`).

### Situational — enter only if the condition applies

| Variable | Enter it when… | Where to get it |
|----------|----------------|-----------------|
| `BOOTH_PUBLIC_HOST` | The venue WiFi isolates clients from each other, so a phone cannot reach your laptop's LAN IP. Run a tunnel (ngrok / Cloudflare Tunnel) and paste its **full URL**, e.g. `https://abc123.ngrok.io` | Your tunnel tool |
| `REPLICATE_API_TOKEN` | You set `DANCE_PROVIDER=replicate` | <https://replicate.com/account> 💳 **PAID**, a separate account from MiniMax |

⚠️ `BOOTH_PUBLIC_HOST` is the single most common day-of failure. If it is blank,
the QR code contains the laptop's LAN IP. That is correct on a normal network
and useless on a guest network with client isolation. **Test one QR scan from a
phone that is actually on the venue WiFi before the doors open.**

### Tuning — sensible defaults already set

| Variable | Default | What it changes |
|----------|---------|-----------------|
| `MINIMAX_VIDEO_MODEL` | `MiniMax-Hailuo-2.3` | Station 1's video model. See the table in Part 3 |
| `MINIMAX_RESOLUTION` | `768P` | 💳 Directly changes what you pay per visitor |
| `MINIMAX_DURATION` | `6` | 💳 Ditto. 6 or 10 seconds |
| `MINIMAX_IMAGE_MODEL` | `image-01` | Stations 2 & 3 |
| `MINIMAX_TEXT_MODEL` | `MiniMax-M3` | ⚠️ The **vision** model. Must be M3-generation — the M2.x series is text-only and will silently ignore the photo it was asked to describe |
| `MINIMAX_TIMEOUT` | `600` | Seconds to wait for a render. Typical is 1–5 minutes |

### Not needed for the booth — legacy demo only

The variables below belong to the older demo apps (Part 6). The booth ignores
them completely. Leave them blank unless you are reviving those files.

| Variable | What it is | Marker |
|----------|-----------|--------|
| `DB_HOST` `DB_PORT` `DB_NAME` `DB_USER` `DB_PASSWORD` | ✏️ Postgres connection, used only if `DB_TYPE=postgres` | Free (self-hosted) |
| `FIREBASE_CREDENTIALS_PATH` `FIREBASE_PROJECT_ID` | ✏️ Firestore, used if `DB_TYPE=firestore` | Free tier available |
| `CLOUDINARY_CLOUD_NAME` `CLOUDINARY_API_KEY` `CLOUDINARY_API_SECRET` | ✏️ Video hosting for the old `app.py` | Free tier available |
| `AI_API_URL` `AI_API_KEY` | ✏️ Generic AI endpoint in the old `generate_video.py` | 💳 **PAID** |
| `API_TOKEN` | ✏️ HuggingFace token for `app2.py`. The endpoint URL is hardcoded at `app2.py:21` | 🆓 free tier, rate limited |

⚠️ `serviceAccountKey.json` in this folder is a **real Firebase private key**
belonging to the legacy demo. It is correctly excluded by `.gitignore` and has
never been committed. **The booth does not use it.** If you are not reviving the
legacy demo, delete the file and revoke that service account — the booth will
not notice.

---

# Part 3 — 💳 What costs money

⚠️ **Read this before pointing the booth at real visitors.** MiniMax has **no
free tier on any station**. Under the previous Gemini setup, Stations 2 and 3
were free and only Station 1 billed. That is no longer true: *every button in
the booth now spends money.* Your `LIMIT_*_DAILY` settings are the only thing
standing between you and an unbounded bill.

### Station 1 (dance video) — the expensive one

MiniMax bills video in **video points**, per clip rather than per second. From
MiniMax's [video pricing page](https://platform.minimax.io/docs/guides/pricing-video):

| Model | Resolution | Duration | Video points |
|-------|-----------|----------|--------------|
| `MiniMax-Hailuo-2.3-Fast` | 768P | 6s | **0.7** |
| `MiniMax-Hailuo-2.3-Fast` | 768P | 10s | 1.1 |
| `MiniMax-Hailuo-2.3-Fast` | 1080P | 6s | 1.3 |
| `MiniMax-Hailuo-2.3` (default) | 768P | 6s | **1.0** |
| `MiniMax-Hailuo-2.3` | 768P | 10s | 2.0 |
| `MiniMax-Hailuo-2.3` | 1080P | 6s | 2.0 |
| `MiniMax-Hailuo-02` | 512P | 6s | **0.3** |
| `MiniMax-Hailuo-02` | 512P | 10s | 0.5 |
| `MiniMax-Hailuo-02` | 768P | 6s | 1.0 |
| `MiniMax-Hailuo-02` | 1080P | 6s | 2.0 |

⚠️ **A video point is not a fixed dollar amount** — it depends on the package
your account is on. MiniMax's published packages work out somewhere around
**$0.22–$0.27 per point**, so the default (Hailuo 2.3, 768P, 6s = 1 point)
lands near **$0.25 per visitor**, and **300 visitors is roughly $75**. Treat
that as an order-of-magnitude figure only, and **check your own billing console**
before committing to a headcount.

**The cheapest real dance video** is `MINIMAX_VIDEO_MODEL=MiniMax-Hailuo-02`
with `MINIMAX_RESOLUTION=512P` at 6 seconds — 0.3 points, roughly a third of the
default. Worth using while rehearsing even if you run the default on the day.

⚠️ Not every model supports every combination. Hailuo-2.3 has **no 512P**, and
1080P is 6-seconds-only everywhere. The booth validates your `.env` against the
table above at startup and refuses a bad combination with a readable message,
rather than letting MiniMax reject a request you have already queued.

To spend nothing at all on Station 1, set `DANCE_PROVIDER=mock`. The full flow
(upload → generate → QR → download) still works; it just produces a slow-zoom
render of the photo rather than a dance. **This is also your fallback if the
paid provider fails mid-event.**

### Stations 2 and 3 (image editing) — 💳 also paid now

Each generation is **two billed MiniMax calls**, not one:

1. A `MiniMax-M3` vision call that reads the visitor's second photo.
2. An `image-01` generation call.

The image call dominates, and image generation is far cheaper per use than
video — but it is **not free**, and there is no `mock` provider for these two
stations. If you want a zero-cost rehearsal of Stations 2 and 3, the honest
answer is that there isn't one: rehearse with a small `LIMIT_*_DAILY` and accept
the small spend.

### Your budget safety net

`LIMIT_*_DAILY` in `.env` is the hard ceiling on generations per day. This is
what stops a stuck refresh key spending a month's budget in an afternoon.
**With MiniMax behind all three stations this matters more than it used to — it
is now the only cap on the entire booth, not just Station 1.** See Part 5.

---

# Part 4 — Station 1: how the MiniMax pipeline works

```
visitor photo ──> normalise (EXIF, downscale, JPEG)
                        │
                        └──> base64 data URI ──> first_frame_image ──┐
                                                                     │
[optional] their clip ──> ffmpeg: 6 frames tiled into one image      │
                                    │                                │
                                    └──> MiniMax-M3 vision           │
                                         "describe this dance"       │
                                                │                    │
                                       movement description ─────────┤
                                                                     │
built-in template ──────> template prompt text ─────────────────────>┤
                                                                     ▼
                                     POST /v1/video_generation  (Hailuo 2.3)
                                                                     │ task_id
                                                                     ▼
                              poll /v1/query/video_generation until "Success"
                                                                     │ file_id
                                                                     ▼
                                     /v1/files/retrieve ──> download_url
                                                                     │
                                                       outputs/dance_xxx.mp4
                                                                     │
                                                          QR code ──> phone
```

Implemented in [`booth/video_dance.py`](booth/video_dance.py), with the shared
HTTP and error-translation layer in
[`booth/minimax_client.py`](booth/minimax_client.py).

**Things the MiniMax API is strict about**, all enforced in code so a bad value
fails with a readable message instead of an opaque HTTP 400:

- **Media goes in inline, as a base64 data URI.** MiniMax accepts a public URL
  or a data URI; a booth laptop on venue WiFi has no public URL, so everything
  is inlined. Input images must be under 20 MB — uploads are downscaled to
  `MAX_INPUT_DIM` long before that matters.
- `duration` is an **integer** (`6`, not `"6s"`), and must be one the chosen
  model actually offers.
- `resolution` must be one of the model's supported values — see Part 3.
- The video prompt is capped at **2000 characters**; image prompts are trimmed
  to `MINIMAX_PROMPT_LIMIT` (1500) before sending.
- ⚠️ **MiniMax returns HTTP 200 for application-level failures**, putting the
  real outcome in `base_resp.status_code`. Checking only the HTTP status is the
  classic way to "succeed" with no output, so every call goes through
  `booth/minimax_client.py`, which checks both that and the v2 error envelope.

### ⚠️ The one limitation worth knowing before you promise anything

**A visitor's own clip is a description, not choreography.**

MiniMax's image-to-video endpoint takes a first frame and a text prompt. It has
**no driving-video input at all**, so a visitor's clip cannot be used as motion
directly. Instead the clip is turned into *words*: ffmpeg pulls six frames into
a single tiled image, `MiniMax-M3` describes the dance in under 70 words, and
that description becomes the prompt.

The result therefore captures the **kind** of dance in their clip — the style,
the energy, roughly what the arms and feet do — not their exact routine. The
booth says so in the `note` it returns, and the UI shows it.

If a visitor expects their precise moves reproduced onto themselves, that needs
`DANCE_PROVIDER=replicate` (Wan 2.2 Animate), which does true frame-by-frame
motion transfer.

### Choosing a provider

Set `DANCE_PROVIDER` in `.env`:

| Value | Real AI? | Visitor's own clip? | Cost | Use when |
|-------|----------|---------------------|------|----------|
| `minimax` | Yes | Yes, as a **style description** | 💳 ~1 video point / 6s @ 768P | **Default.** One key for the whole booth |
| `mock` | No | n/a | 🆓 Free | Testing, rehearsal, and your day-of fallback |
| `replicate` | Yes | Yes, **true motion transfer** | 💳 ~$0.20–0.40 / 5s | You need the exact choreography copied |

`replicate` needs driving videos in `dance_templates/` for the built-in
templates — see [`dance_templates/README.md`](dance_templates/README.md).
MiniMax does not; it works from the template's text prompt.

---

# Part 4b — Stations 2 & 3: why they take two API calls

This is the biggest structural difference from the previous Gemini build, and it
changes what you should promise visitors.

```
visitor photo ──────────────> subject_reference[type=character] ──┐
                                                                  │
second photo ──> MiniMax-M3 vision ──> "a red denim jacket, …" ──> prompt
                                                                  │
                                       POST /v1/image_generation (image-01)
```

MiniMax `image-01` accepts **exactly one reference image**, and it must be a
`character` subject reference. There is no second-image slot, no mask, and no
inpainting region. So the two-photo stations cannot hand both photos to the
model the way a native multi-image editor would.

What happens instead: the **second** photo (the reference look, or the
environment) is described in words by the vision model, that description is
folded into the text prompt, and the **first** photo (the visitor) goes in as
the character reference.

⚠️ **This is a paraphrase, not a composite.** The output matches the
*description* of the second photo rather than its pixels — a specific jacket
becomes "a red denim jacket", and a specific void deck becomes "a covered
concrete walkway with blue pillars". Expect a good likeness of the **person**
and a plausible-but-not-identical rendering of the **reference**. If someone
brings a photo of a specific place expecting to see that exact place, set
expectations at the counter.

The wording of those description requests is tuned in
[`booth/prompts.py`](booth/prompts.py) (`EDIT_REFERENCE_QUESTION` and
`SCENE_REFERENCE_QUESTION`). They deliberately ask for compact, concrete visual
attributes and no preamble, because every wasted character eats into the
1500-character image prompt budget.

---

# Part 5 — Rate limits

Two independent ceilings, both in `.env`:

- **Per session** (`LIMIT_*_SESSION`) — stops one visitor hogging the booth.
  Tracked by a cookie, so it resets if someone clears their browser. Good
  manners, not a security control.
- **Per day** (`LIMIT_*_DAILY`) — 💳 **the real budget guard.** This is the
  number that caps your spend.

| Action | Session default | Daily default |
|--------|-----------------|---------------|
| `dance_template` | 3 | 300 |
| `dance_custom` | 1 | 100 |
| `edit_image` | 5 | 400 |
| `scene_image` | 5 | 400 |

Custom dance clips are capped hardest because that path is the expensive one.

⚠️ These defaults were set when Stations 2 and 3 ran on a free tier, so 400/day
each cost nothing. **On MiniMax they do cost money.** Revisit the `EDIT` and
`SCENE` daily numbers against your budget rather than inheriting them.

Counts live in `booth_usage.db` (SQLite) and survive restarts. A generation that
fails through no fault of the visitor is **automatically refunded**. Delete the
file to reset everything.

⚠️ `DISABLE_RATE_LIMITS=true` removes all ceilings. It is for development only.
Never set it at an event.

---

# Part 6 — What every file does

### The booth (current, this is what runs)

| File | Role |
|------|------|
| [`booth_app.py`](booth_app.py) | Flask server. Routes, upload normalisation, session cookies, QR payloads, health check |
| [`booth/minimax_client.py`](booth/minimax_client.py) | Shared MiniMax plumbing: base URL, key, request/response handling, error translation |
| [`booth/video_dance.py`](booth/video_dance.py) | Station 1. All three video providers behind one interface |
| [`booth/minimax_image.py`](booth/minimax_image.py) | Stations 2 & 3. Vision description and image generation |
| [`booth/prompts.py`](booth/prompts.py) | Prompt templates and presets. Identity and quality rules live here |
| [`booth/limits.py`](booth/limits.py) | SQLite rate limiting, consume / refund / stats |
| [`booth.html`](booth.html), [`css/booth.css`](css/booth.css), [`js/booth.js`](js/booth.js) | Kiosk UI |
| [`generate_qr.py`](generate_qr.py) | QR generation (`qrcode` library — produces genuinely scannable codes) |
| [`requirements.txt`](requirements.txt) | Booth dependencies, pinned to tested versions |

All MiniMax calls are plain REST over HTTPS, so there is **no vendor SDK to
install** — `requests` is the only client needed.

### HTTP endpoints

| Route | Purpose |
|-------|---------|
| `GET /` | The booth screen |
| `GET /api/config` | Templates, presets, and this session's remaining quota |
| `GET /api/health` | ⚠️ **Check this before the doors open.** 503 if MiniMax is not reachable |
| `GET /api/stats` | Today's usage counts |
| `POST /api/dance` | Station 1 — `photo`, `template_id`, optional `dance_video` |
| `POST /api/edit` | Station 2 — `photo`, `reference`, `preset_id`, `request` |
| `POST /api/scene` | Station 3 — `photo`, `environment`, `preset_id`, `request` |
| `GET /outputs/<f>` · `GET /download/<f>` | View / download a result |

`/api/health` probes the key **once** and reports the image stations and the
video station separately, because the booth can run usefully with images working
and video down, or the reverse. The probe is a one-token text call — it costs a
fraction of a cent rather than a generation, so it is safe to poll.

### Legacy demo (kept, untouched, not wired to the booth)

| File | What it actually does |
|------|----------------------|
| [`app.py`](app.py) | The original Flask dance wizard |
| [`js/dance-engine.js`](js/dance-engine.js) | ⚠️ The original "AI". A canvas **stick figure** driven by sine waves. Not a model |
| [`generate_video.py`](generate_video.py) | ⚠️ POSTs to an AI API but **never reads the response**, then renders 8 seconds of solid dark blue |
| [`js/qr-generator.js`](js/qr-generator.js) | ⚠️ Hand-rolled QR generator with no Reed-Solomon and no masking. **Does not scan** |
| [`app2.py`](app2.py) | Streamlit "Void Deck Makeover" using HuggingFace SD 1.5 inpainting. The only legacy file that calls a real model *and uses the result* |
| [`database.py`](database.py), [`firebase_setup.py`](firebase_setup.py) | Firestore / Postgres persistence |
| [`upload_video.py`](upload_video.py) | Cloudinary upload |
| [`main.py`](main.py), [`test_database.py`](test_database.py), `app3.py` | CLI harness, one DB test, and an empty file |
| [`requirements-legacy.txt`](requirements-legacy.txt) | Heavier native deps for the above. Deliberately separate so a build failure there cannot block the booth |

The booth replaces `app.py` and `index.html`. Both still run; nothing was
deleted. The legacy demo's Firestore option is the **only** remaining Google
touchpoint in this repo, and the booth never calls it.

---

# Part 7 — Before the doors open

- [ ] `python -m booth.minimax_image` prints "API key works"
- [ ] `GET /api/health` returns **200** — this checks the key, the image models
      *and* the Station 1 video settings
- [ ] Confirm `MINIMAX_API_BASE` matches the region you signed up in
- [ ] Generate one result at each of the three stations
- [ ] **Scan a QR code with a phone that is on the venue WiFi** and confirm the
      download works. ⚠️ This is the step that most often fails on the day
- [ ] 💳 Confirm the MiniMax account has **credit on it** — an empty balance
      fails every station at once
- [ ] 💳 Confirm `LIMIT_*_DAILY` matches your budget, **including edit/scene**
- [ ] 💳 Confirm `MINIMAX_VIDEO_MODEL`, `MINIMAX_RESOLUTION` and
      `MINIMAX_DURATION` are what you meant to pay for
- [ ] `ffmpeg -version` works, if you are offering the "bring your own clip" path
- [ ] Know your fallback: set `DANCE_PROVIDER=mock`, restart, keep the queue
      moving

---

# Part 8 — Privacy

Visitors are handing you photos of their families. Decide and **post on the
booth** how you handle that.

What the code does today:

- Uploads are processed in memory; only the **generated output** is written to
  `outputs/`, which is gitignored.
- Every station sends the visitor's photo to **MiniMax** (`api.minimax.io`, or
  the mainland host if you configured it) as inline base64. Nothing is uploaded
  to a persistent file store on the way in, but MiniMax necessarily receives and
  processes the image.
- A visitor's uploaded dance clip is written to `uploads/` only long enough for
  ffmpeg to read six frames from it, then deleted in a `finally` block. **The
  clip itself is never sent to MiniMax** — only the tiled frame image, and only
  so the vision model can describe the movement.
- ⚠️ **The finished video is stored on MiniMax's side**, and the booth downloads
  it from there via `/v1/files/retrieve`. That copy persists on MiniMax until
  their retention window expires. This is out of your control.
- Nothing is deleted from `outputs/` automatically. A nightly cron emptying that
  directory is the simplest honest answer to "how long do you keep it?"

⚠️ There is **no setting in this booth that loosens or tightens content
filtering.** MiniMax applies its own filters to both input (code `1026`) and
output (code `1027`); the booth translates both into a plain-language message.
If a family photo comes back refused, that is the safety filter, and the answer
is a different photo.

⚠️ Check MiniMax's current terms on whether API data may be used for model
training before you tell visitors anything about it. Do not repeat assurances
inherited from a previous provider — they do not carry over.

---

# Part 9 — Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `/api/health` 503, `"MINIMAX_API_KEY is not set"` | ✏️ You have not created `.env`, or the key line is blank |
| `"MiniMax rejected the API key"` (code `1004`) | ⚠️ Wrong key — **or the right key on the wrong region.** Check `MINIMAX_API_BASE`: `api.minimax.io` (international) vs `api.minimaxi.com` (mainland China). Keys are not interchangeable |
| `"has run out of credit"` (code `1008`) | 💳 Top up at <https://platform.minimax.io/user-center/payment>. This kills all three stations at once |
| `"MiniMax rate limit hit"` (code `1002`) | Too many concurrent requests. Wait a few seconds; lower the session limits if it recurs at the counter |
| `"content filter blocked this input"` (`1026`) / `"…the generated result"` (`1027`) | The safety filter. Try a different photo — no config setting overrides it |
| `does not support MINIMAX_RESOLUTION=…` | Your model/resolution pair is invalid — e.g. 512P on Hailuo-2.3. See the table in Part 3 |
| `at 1080P only supports MINIMAX_DURATION=6` | 1080P is 6-seconds-only on every current model |
| `"MiniMax is still working after 600s"` | ⚠️ **Check the MiniMax console before retrying** — the render may yet finish, and you have already been billed. Raise `MINIMAX_TIMEOUT` if it recurs |
| Station 1 returns a still image | `mock` provider with no ffmpeg installed |
| `"needs ffmpeg installed"` on a visitor's clip | ffmpeg is not on PATH. Install it, use a built-in template, or switch to `replicate` |
| Their clip produced a different dance | ⚠️ Expected. The clip is a *description*, not choreography — see Part 4. Use `replicate` for exact motion |
| The reference photo's exact jacket/place didn't come through | ⚠️ Expected on Stations 2 & 3 — see Part 4b. `image-01` takes one reference image and it has to be the person |
| QR scans but the download times out | ✏️ `BOOTH_PUBLIC_HOST` — the phone cannot reach your LAN IP. Use a tunnel |
| Photo descriptions are generic or ignore the image | ⚠️ `MINIMAX_TEXT_MODEL` is set to an M2.x model. Those are **text-only** and silently drop the image. Use `MiniMax-M3` |
| First request after startup hangs forever | Fixed. If it recurs, it is a lock in `booth/limits.py` — `_lock` must stay an `RLock` |
| Which models am I on? | `python -m booth.minimax_image` prints them and validates the key |
