"""
Prompt templates for the two image stations.

This is the file to tune during the event - wording changes here take effect on
the next request, no restart needed beyond reloading the Flask dev server.

Two things shape everything here:

1. The identity clause is load-bearing. Image models drift towards "generic
   attractive person" unless you keep telling them not to, and at a booth the
   single thing that makes or breaks the demo is whether visitors recognise
   themselves in the output.

2. MiniMax image-01 takes ONE reference image and a text prompt, with a prompt
   budget around 1500 characters. The visitor's second photo therefore arrives
   here as a *description* produced by the vision model, not as an image. So
   the rules below are deliberately terse - every character spent on style
   advice is a character not spent describing the visitor's actual reference.
"""

# Short on purpose. See note 2 above.
IDENTITY_RULE = (
    "Keep the person's face, bone structure, skin tone, hairstyle and apparent "
    "age exactly as in the reference photo - they must be instantly "
    "recognisable. Do not beautify, slim or lighten them."
)

QUALITY_RULE = (
    "Photorealistic. Natural light matching the scene, believable contact "
    "shadows, sharp focus on the face. No text, no watermark, no extra limbs."
)

# What the vision model is asked about the visitor's SECOND photo. The answer is
# pasted into the image prompt, so it must be compact and visual - no preamble,
# no "this image shows", no interpretation.
EDIT_REFERENCE_QUESTION = (
    "Describe only the visual style of this image in under 60 words, as a list "
    "of concrete visual attributes: clothing and its colours and materials, art "
    "style or medium, colour grading, lighting, and era if evident. Do not "
    "describe any person's identity or face. Reply with the description only, "
    "no preamble."
)

SCENE_REFERENCE_QUESTION = (
    "Describe this place in under 60 words as concrete visual detail: the type "
    "of location, its architecture and materials, colours, notable objects, "
    "time of day and weather. Do not mention any people. Reply with the "
    "description only, no preamble."
)

# Station 2 - person photo + reference photo + what they want changed.
EDIT_PRESETS = [
    {
        "id": "outfit",
        "name": "Wear this outfit",
        "emoji": "👗",
        "instruction": (
            "Dress the person in the clothing described in the reference below. "
            "Keep their pose and a simple, clean background."
        ),
    },
    {
        "id": "style",
        "name": "Match this art style",
        "emoji": "🎨",
        "instruction": (
            "Render the person in the artistic style described in the reference "
            "below, keeping their likeness intact."
        ),
    },
    {
        "id": "add_person",
        "name": "Studio portrait",
        "emoji": "🫂",
        "instruction": (
            "Create a natural portrait of the person in the setting and mood "
            "described in the reference below."
        ),
    },
    {
        "id": "era",
        "name": "Time travel",
        "emoji": "⏳",
        "instruction": (
            "Restyle the person to fit the time period and mood described in the "
            "reference below, with period-appropriate clothing, hair and film grain."
        ),
    },
]

# Station 3 - person photo + environment photo.
SCENE_PRESETS = [
    {
        "id": "place_me",
        "name": "Put me here",
        "emoji": "📍",
        "instruction": (
            "Place the person naturally into the location described below, at a "
            "believable size and standing position."
        ),
    },
    {
        "id": "golden_hour",
        "name": "Golden hour",
        "emoji": "🌅",
        "instruction": (
            "Place the person into the location described below, relit for warm "
            "golden-hour sunlight with long soft shadows."
        ),
    },
    {
        "id": "festive",
        "name": "Festive makeover",
        "emoji": "🎉",
        "instruction": (
            "Place the person into the location described below, decorated for a "
            "lively community celebration with lights, banners and greenery."
        ),
    },
    {
        "id": "dream_upgrade",
        "name": "Dream upgrade",
        "emoji": "✨",
        "instruction": (
            "Place the person into the location described below, reimagined as a "
            "beautifully renovated, welcoming version of itself while keeping "
            "its recognisable layout."
        ),
    },
]


def _find(presets, preset_id):
    for preset in presets:
        if preset["id"] == preset_id:
            return preset
    return None


def _assemble(base, reference_description, user_request, extra=None):
    parts = [base]
    if reference_description:
        parts.append(f"Reference: {reference_description.strip()}")
    if extra:
        parts.append(extra)
    if user_request and user_request.strip():
        parts.append(f"The visitor asked for: {user_request.strip()}")
    parts += [IDENTITY_RULE, QUALITY_RULE]
    return "\n\n".join(parts)


def build_edit_prompt(preset_id, user_request="", reference_description=""):
    """
    Subject = the visitor's photo (sent as the character reference).
    reference_description = the vision model's read of their second photo.
    """
    preset = _find(EDIT_PRESETS, preset_id)
    base = preset["instruction"] if preset else (
        "Restyle the person according to the reference described below."
    )
    return _assemble(base, reference_description, user_request)


def build_scene_prompt(preset_id, user_request="", reference_description=""):
    """
    Subject = the visitor's photo (sent as the character reference).
    reference_description = the vision model's read of their environment photo.
    """
    preset = _find(SCENE_PRESETS, preset_id)
    base = preset["instruction"] if preset else (
        "Place the person into the location described below."
    )
    return _assemble(
        base, reference_description, user_request,
        extra="Keep the location recognisably itself - a visitor should still be "
              "able to tell where it is.",
    )
