# Chengsan × DADE — Interactive Booth

A three-station photo/video booth for community events. Visitors upload a photo
and walk away with something they can scan and take home.

| # | Station | Visitor gives | Gets back | Model | Cost |
|---|---------|---------------|-----------|-------|------|
| 1 | **Make me dance** | A photo, plus either a built-in dance template **or** their own dance clip | A dance video of themselves | Gemini Omni 1.1 Flash | 💳 **PAID** |
| 2 | **Edit my photo** | Their photo + a reference photo | An edited image | Gemini image | 🆓 free tier |
| 3 | **Put me somewhere** | Their photo + an environment photo | Them composited into that place | Gemini image | 🆓 free tier |

Every result is written to `outputs/` and offered as a QR code pointing at the
booth laptop's LAN address, so a visitor scans and downloads to their phone.

---

## Legend used throughout this document

| Marker | Meaning |
|--------|---------|
| 💳 **PAID** | Costs real money per use. Needs billing enabled. |
| 🆓 | Runs on a free tier. |
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
It is not strictly required, but without it the offline `mock` renderer produces
a still image instead of a video, and visitor-supplied dance clips are uploaded
untrimmed (slow).

---

# Part 2 — ✏️ Everything YOU have to enter

These are the only values that are not already filled in. Everything else in
`.env.example` has a working default.

### Required — the booth will not start without this

| Variable | Where to get it | Notes |
|----------|-----------------|-------|
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> | ✏️ **YOU ENTER.** One key powers all three stations. For Station 1 the project behind this key must also have 💳 **billing enabled** — see Part 3. |

### Situational — enter only if the condition applies

| Variable | Enter it when… | Where to get it |
|----------|----------------|-----------------|
| `BOOTH_PUBLIC_HOST` | The venue WiFi isolates clients from each other, so a phone cannot reach your laptop's LAN IP. Run a tunnel (ngrok / Cloudflare Tunnel) and paste its **full URL**, e.g. `https://abc123.ngrok.io` | Your tunnel tool |
| `REPLICATE_API_TOKEN` | You set `DANCE_PROVIDER=replicate` | <https://replicate.com/account> 💳 **PAID** |
| `GEMINI_IMAGE_MODEL` | You want to pin one image model instead of auto-detecting | Run `python -m booth.gemini_image` to list what your key can reach |

⚠️ `BOOTH_PUBLIC_HOST` is the single most common day-of failure. If it is blank,
the QR code contains the laptop's LAN IP. That is correct on a normal network
and useless on a guest network with client isolation. **Test one QR scan from a
phone that is actually on the venue WiFi before the doors open.**

### Not needed for the booth — legacy demo only

The variables below belong to the older demo apps (Part 6). The booth ignores
them completely. Leave them blank unless you are reviving those files.

| Variable | What it is | Marker |
|----------|-----------|--------|
| `DB_HOST` `DB_PORT` `DB_NAME` `DB_USER` `DB_PASSWORD` | ✏️ Postgres connection, used only if `DB_TYPE=postgres` | Free (self-hosted) |
| `FIREBASE_CREDENTIALS_PATH` `FIREBASE_PROJECT_ID` | ✏️ Firestore, used if `DB_TYPE=firestore` (the default in that old code) | Free tier available |
| `CLOUDINARY_CLOUD_NAME` `CLOUDINARY_API_KEY` `CLOUDINARY_API_SECRET` | ✏️ Video hosting for the old `app.py` | Free tier available |
| `AI_API_URL` `AI_API_KEY` | ✏️ Generic AI endpoint in the old `generate_video.py`. Defaults to `https://api.replicate.com/v1/predictions` | 💳 **PAID** |
| `API_TOKEN` | ✏️ HuggingFace token for `app2.py`. The endpoint URL is hardcoded at `app2.py:21` | 🆓 free tier, rate limited |

⚠️ `serviceAccountKey.json` in this folder is a **real Firebase private key**.
It is correctly excluded by `.gitignore` and has never been committed. Do not
remove that ignore rule, and do not paste the file's contents anywhere.

---

# Part 3 — 💳 What costs money

### Station 1 (dance video) — 💳 PAID, no way around it

**No Gemini video model has a free tier.** Gemini Omni 1.1 Flash bills per
second of output video, so the duration you configure is literally your price
per visitor.

| Resolution | Approx. rate | 6-second clip |
|------------|--------------|---------------|
| `360p` | ~$0.03/sec | **~$0.18** |
| `720p` (default) | ~$0.10/sec | **~$0.60** |
| `1080p` | ~$0.15/sec | ~$0.90 |
| `4k` | ~$0.30/sec | ~$1.80 |

⚠️ **At 720p, 300 visitors is roughly $180.** Set `OMNI_RESOLUTION=360p` and
`OMNI_DURATION=3` while testing, and decide deliberately before the event. Rates
change — check <https://ai.google.dev/pricing> against your own billing console.

To spend nothing at all, set `DANCE_PROVIDER=mock`. The full flow (upload →
generate → QR → download) still works; it just produces a slow-zoom render of
the photo rather than a dance. This is also your fallback if the paid provider
fails mid-event.

### Stations 2 and 3 (image editing) — 🆓 free

Verified against Google's pricing page on 2026-08-31:

| Model | Free tier | Note |
|-------|-----------|------|
| `gemini-2.5-flash-image` | ✅ Yes, ~500 images/day | ⚠️ **Retires 2026-10-16** |
| `gemini-3.1-flash-image` | ❌ No | 💳 Paid only |
| `gemini-3-pro-image` | ❌ No | 💳 Paid only, highest quality |

The booth ships with `GEMINI_PREFER_FREE_TIER=true`, which pins it to the only
free option. Flip it to `false` once billing is on.

⚠️ **You will have to flip it before 16 October 2026**, when the free model is
retired along with the rest of the 2.5 series. After that date, all three
stations are 💳 paid.

### Your budget safety net

`LIMIT_*_DAILY` in `.env` is the hard ceiling on generations per day. This is
what stops a stuck refresh key spending a month's budget in an afternoon.
**Set it deliberately before you point Station 1 at a paid provider.** See
Part 5.

---

# Part 4 — Station 1: how the Gemini Omni pipeline works

```
visitor photo ──> normalise (EXIF, downscale, JPEG)
                        │
                        ├──> Files API upload ──> file URI ──┐
                        │                                     │
[optional] their clip ──> ffmpeg trim to ~3s ──> Files API ──┤
                        │                                     │
built-in template ──────> prompt text ────────────────────────┤
                                                              ▼
                                        interactions.create(gemini-omni-1.1-flash)
                                                              │
                                                     output_video.uri
                                                              │
                                              files.download ──> outputs/dance_xxx.mp4
                                                              │
                                                        QR code ──> visitor's phone
```

Implemented in [`booth/video_dance.py`](booth/video_dance.py).

**Things the Interactions API is strict about**, all enforced in code so a bad
value fails with a readable message instead of an opaque HTTP 400:

- Media goes in **by File API URI only**. Inline bytes are not accepted in an
  interaction input part, so the photo is uploaded first (`_upload_for_omni`).
- `duration` must be a **string with the unit** — `"6s"`, not `"6"` — and an
  integer from **3 to 10**.
- `resolution` must be exactly one of `360p`, `720p`, `1080p`, `4k`.
- Omni gets its **own SDK client with a 10-minute HTTP timeout**
  (`OMNI_TIMEOUT`). The default timeout is far shorter than a video render, so
  sharing the image client would abort a request you had already been billed for.
- `<FIRST_FRAME>` binds the photo as the opening frame; `<VIDEO_REF_0>` binds
  the visitor's clip as a motion reference.

### ⚠️ Two limitations worth knowing before you promise anything

**1. A reference clip is a style hint, not choreography.** Omni treats
`<VIDEO_REF_0>` as a ~3-second motion and character reference. It captures the
*feel* of a dance. It does **not** reproduce a specific routine frame by frame.
If a visitor expects to see their exact moves copied onto themselves, use
`DANCE_PROVIDER=replicate` (Wan 2.2 Animate), which does true motion transfer.

**2. Reference-video upload is geo-restricted.** Uploading videos for edits,
extensions, or references is **not available in the EEA, Switzerland, the UK,
and some US states**. In those regions the request completes with empty output.
The booth detects this and says so explicitly rather than failing silently — but
if you are running there, the "bring your own clip" half of Station 1 will not
work on Omni. Use `replicate` for that path.

### Choosing a provider

Set `DANCE_PROVIDER` in `.env`:

| Value | Real AI? | Visitor's own clip? | Cost | Use when |
|-------|----------|---------------------|------|----------|
| `gemini_omni` | Yes | Yes (as a ~3s style hint) | 💳 ~$0.60 / 6s @ 720p | **Default.** One key, both halves of Station 1 |
| `mock` | No | n/a | 🆓 Free | Testing, rehearsal, and your day-of fallback |
| `replicate` | Yes | Yes (true motion transfer) | 💳 ~$0.20–0.40 / 5s | You need the exact choreography copied, or you are geo-blocked from Omni |
| `veo` | Yes | ❌ No, templates only | 💳 ~$0.03–0.40/sec | Legacy accounts with Veo but not Omni access |

`replicate` and `veo` need driving videos in `dance_templates/` for the built-in
templates — see [`dance_templates/README.md`](dance_templates/README.md). Omni
does not; it works from the template's text prompt.

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

Counts live in `booth_usage.db` (SQLite) and survive restarts. A generation that
fails through no fault of the visitor is **automatically refunded**. Delete the
file to reset everything.

⚠️ `DISABLE_RATE_LIMITS=true` removes all ceilings. It is for development only.
Never set it at an event with a paid provider active.

---

# Part 6 — What every file does

### The booth (current, this is what runs)

| File | Role |
|------|------|
| [`booth_app.py`](booth_app.py) | Flask server. Routes, upload normalisation, session cookies, QR payloads, health check |
| [`booth/video_dance.py`](booth/video_dance.py) | Station 1. All four video providers behind one interface |
| [`booth/gemini_image.py`](booth/gemini_image.py) | Stations 2 & 3. Image model discovery and generation |
| [`booth/prompts.py`](booth/prompts.py) | Prompt templates and presets. Identity and quality rules live here |
| [`booth/limits.py`](booth/limits.py) | SQLite rate limiting, consume / refund / stats |
| [`booth.html`](booth.html), [`css/booth.css`](css/booth.css), [`js/booth.js`](js/booth.js) | Kiosk UI |
| [`generate_qr.py`](generate_qr.py) | QR generation (`qrcode` library — produces genuinely scannable codes) |
| [`requirements.txt`](requirements.txt) | Booth dependencies, pinned to tested versions |

### HTTP endpoints

| Route | Purpose |
|-------|---------|
| `GET /` | The booth screen |
| `GET /api/config` | Templates, presets, and this session's remaining quota |
| `GET /api/health` | ⚠️ **Check this before the doors open.** 503 if Gemini or Omni is not reachable |
| `GET /api/stats` | Today's usage counts |
| `POST /api/dance` | Station 1 — `photo`, `template_id`, optional `dance_video` |
| `POST /api/edit` | Station 2 — `photo`, `reference`, `preset_id`, `request` |
| `POST /api/scene` | Station 3 — `photo`, `environment`, `preset_id`, `request` |
| `GET /outputs/<f>` · `GET /download/<f>` | View / download a result |

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
deleted.

---

# Part 7 — Before the doors open

- [ ] `GET /api/health` returns **200** — this now checks the image model *and*
      Omni reachability
- [ ] Generate one result at each of the three stations
- [ ] **Scan a QR code with a phone that is on the venue WiFi** and confirm the
      download works. ⚠️ This is the step that most often fails on the day
- [ ] Confirm `LIMIT_*_DAILY` matches your 💳 budget
- [ ] Confirm `OMNI_RESOLUTION` and `OMNI_DURATION` are what you meant to pay for
- [ ] Know your fallback: set `DANCE_PROVIDER=mock`, restart, keep the queue moving

---

# Part 8 — Privacy

Visitors are handing you photos of their families. Decide and **post on the
booth** how you handle that.

What the code does today:

- Uploads are processed in memory; only the **generated output** is written to
  `outputs/`, which is gitignored.
- Station 1 is the exception: the photo and any clip are **uploaded to Google's
  Files API** because Omni requires URI inputs. Local temp copies are deleted in
  a `finally` block, but the copy on Google's side persists until their
  retention window expires.
- Nothing is deleted from `outputs/` automatically. A nightly cron emptying that
  directory is the simplest honest answer to "how long do you keep it?"

⚠️ `GEMINI_ALLOW_MINORS` **does nothing on this setup.** The underlying
`person_generation` option is Vertex AI-only — the SDK rejects it client-side on
the plain-API-key path, for every model. The booth therefore only sends it if
you move to Vertex. On an API key, photos containing children are handled by the
model's default behaviour, and there is no setting here that loosens or tightens
it. If a family photo comes back refused, that is the safety filter, and the
answer is a different photo.

⚠️ Google's terms on whether **free-tier** API data may be used for product
improvement differ from paid tiers. Check the current terms before you tell
visitors anything about it.

---

# Part 9 — Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `/api/health` returns 503, "GEMINI_API_KEY is not set" | ✏️ You have not created `.env`, or the key line is blank |
| `"Gemini Omni quota reached"` / `"can't reach Gemini Omni"` | 💳 Billing is not enabled on the key's project. Omni has no free tier |
| `"Free-tier quota reached"` on Station 2 or 3 | ~500 images/day used. Resets at midnight Pacific |
| Omni finishes fast and returns nothing, with a clip attached | ⚠️ The EEA/UK/Switzerland geo-restriction. Use a template, or `DANCE_PROVIDER=replicate` |
| `OMNI_DURATION must be between 3 and 10` | Omni's hard limit. Cost is per second, so 3 is also the cheapest |
| Station 1 returns a still image | `mock` provider with no ffmpeg installed |
| QR scans but the download times out | ✏️ `BOOTH_PUBLIC_HOST` — the phone cannot reach your LAN IP. Use a tunnel |
| `"The model returned nothing"` | The safety filter blocked the photo. Try a different one — no config setting overrides this |
| `person_generation parameter is only supported in…` | You reintroduced `person_generation` on the API-key path. It is Vertex-only |
| First request after startup hangs forever | Fixed. If it recurs, it is a lock in `booth/limits.py` — `_lock` must stay an `RLock` |
| Which image model am I on? | `python -m booth.gemini_image` lists everything your key can reach |
