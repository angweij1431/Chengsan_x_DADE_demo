"""
One-off script: generate a single sample dance video on MiniMax-Hailuo-02.

Reads .env, sends test_guy.jpg to the kpop_idol template, and saves the
result under outputs/. This is a REAL, BILLED MiniMax call.

Set DRIVING_VIDEO_PATH to a clip of your own on disk to use that instead of a
built-in template: ffmpeg pulls frames from it, the vision model describes the
moves, and that description drives the MiniMax generation (one extra billed
vision call on top of the video). Requires ffmpeg on PATH. Leave it as None
to use TEMPLATE_ID instead.

Run:  .venv\\Scripts\\python.exe sample_dance.py
"""

from dotenv import load_dotenv
load_dotenv()

from booth.video_dance import generate_dance, DanceError, get_provider

PHOTO_PATH = "uploads/kylian.jpg"
TEMPLATE_ID = "kpop_idol"  # chill_groove | ballroom_waltz | kpop_idol | runway_pose | my_template
DRIVING_VIDEO_PATH = None  # e.g. "my_dance.mp4" - overrides TEMPLATE_ID when set

print(f"Provider: {get_provider()}")

with open(PHOTO_PATH, "rb") as f:
    photo_bytes = f.read()

try:
    result = generate_dance(
        person_image=(photo_bytes, "image/jpeg"),
        template_id=TEMPLATE_ID,
        driving_video_path=DRIVING_VIDEO_PATH,
    )
except DanceError as e:
    print(f"FAILED: {e}")
    raise SystemExit(1)

print("\nSuccess.")
print(f"  file    : {result['video_path']}")
print(f"  provider: {result['provider']}")
print(f"  template: {result['template']}")
if result["note"]:
    print(f"  note    : {result['note']}")
