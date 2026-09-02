# Dance templates (driving videos)

Motion-transfer models (`DANCE_PROVIDER=replicate`) need a **driving video**:
a real clip of someone dancing, whose motion gets copied onto the visitor's
photo. Drop those clips here, named to match `TEMPLATES` in
`booth/video_dance.py`:

| File                 | Template        |
| -------------------- | --------------- |
| `cyber_hiphop.mp4`   | Cyber Hip-Hop   |
| `salsa_fiesta.mp4`   | Salsa Fiesta    |
| `kpop_idol.mp4`      | K-Pop Idol      |
| `breakdance.mp4`     | Breakdance      |

## What makes a good driving clip

- **5-10 seconds.** Cost scales with length, and visitors won't wait.
- **One person, full body in frame the whole time**, feet visible. If limbs
  leave the frame the output tends to smear.
- **Static camera.** Motion transfer copies body movement, not camera movement;
  a moving camera confuses the pose tracker.
- **Plain background, good lighting.** Helps segmentation find the dancer.
- **Portrait 9:16** if visitors will view results on phones.

## Licensing — please read

These clips are redistributed inside every video the booth generates. Do not
use music videos, TikToks, or anything scraped from social media. Use one of:

- footage your team films yourselves (easiest, and it looks on-brand),
- properly licensed stock, or
- clips under a licence that permits derivative works.

`DANCE_PROVIDER=mock` and `DANCE_PROVIDER=veo` do not read this folder — mock
renders locally, and Veo is prompt-driven and cannot follow a driving clip.
