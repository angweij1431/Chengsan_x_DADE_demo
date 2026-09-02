"""
Prompt templates for the two image stations.

This is the file to tune during the event - wording changes here take effect on
the next request, no restart needed beyond reloading the Flask dev server.

The identity clause is the load-bearing part. Image models drift towards
"generic attractive person" unless you keep telling them not to, and at a booth
the single thing that makes or breaks the demo is whether visitors recognise
themselves in the output.
"""

IDENTITY_RULE = (
    "Critically important: preserve the exact facial identity, bone structure, "
    "skin tone, hairstyle and apparent age of every person from the first photo. "
    "They must be immediately recognisable as the same people. Do not beautify, "
    "slim, lighten, or otherwise alter their faces or bodies."
)

QUALITY_RULE = (
    "Photorealistic, natural lighting that matches the scene, correct perspective "
    "and scale, believable contact shadows where people meet the ground. "
    "Sharp focus on faces. No text, no watermarks, no extra limbs or fingers."
)

# Station 2 - person photo + reference photo + what they want changed.
EDIT_PRESETS = [
    {
        "id": "outfit",
        "name": "Wear this outfit",
        "emoji": "👗",
        "instruction": (
            "Dress the people from the first photo in the clothing shown in the "
            "second photo. Keep their pose, body shape and the original background."
        ),
    },
    {
        "id": "style",
        "name": "Match this art style",
        "emoji": "🎨",
        "instruction": (
            "Re-render the first photo in the artistic style of the second photo. "
            "Keep the composition and everyone's likeness intact."
        ),
    },
    {
        "id": "add_person",
        "name": "Put us together",
        "emoji": "🫂",
        "instruction": (
            "Combine the people from both photos into one natural group portrait, "
            "as though they were photographed together at the same moment. "
            "Match lighting and colour grading across both."
        ),
    },
    {
        "id": "era",
        "name": "Time travel",
        "emoji": "⏳",
        "instruction": (
            "Restyle the people from the first photo to fit the time period and "
            "mood of the second photo, including period-appropriate clothing, "
            "hair and film grain."
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
            "Place the people from the first photo naturally into the environment "
            "from the second photo, at a believable size and standing position."
        ),
    },
    {
        "id": "golden_hour",
        "name": "Golden hour",
        "emoji": "🌅",
        "instruction": (
            "Place the people from the first photo into the environment from the "
            "second photo, relit for warm golden-hour sunlight with long soft shadows."
        ),
    },
    {
        "id": "festive",
        "name": "Festive makeover",
        "emoji": "🎉",
        "instruction": (
            "Place the people from the first photo into the environment from the "
            "second photo, and decorate that environment for a lively community "
            "celebration with lights, banners and greenery."
        ),
    },
    {
        "id": "dream_upgrade",
        "name": "Dream upgrade",
        "emoji": "✨",
        "instruction": (
            "Place the people from the first photo into the environment from the "
            "second photo, reimagining that space as a beautifully renovated, "
            "welcoming version of itself while keeping its recognisable layout."
        ),
    },
]


def _find(presets, preset_id):
    for preset in presets:
        if preset["id"] == preset_id:
            return preset
    return None


def build_edit_prompt(preset_id, user_request=""):
    """First photo = the visitor. Second photo = their reference."""
    preset = _find(EDIT_PRESETS, preset_id)
    base = preset["instruction"] if preset else (
        "Edit the first photo using the second photo as the reference for what to change."
    )
    parts = [
        "You are given two photos. The FIRST is the visitor (and their family). "
        "The SECOND is their reference image.",
        base,
    ]
    if user_request.strip():
        parts.append(f"The visitor specifically asked for: {user_request.strip()}")
    parts += [IDENTITY_RULE, QUALITY_RULE]
    return "\n\n".join(parts)


def build_scene_prompt(preset_id, user_request=""):
    """First photo = the visitor. Second photo = the environment."""
    preset = _find(SCENE_PRESETS, preset_id)
    base = preset["instruction"] if preset else (
        "Place the people from the first photo into the environment from the second photo."
    )
    parts = [
        "You are given two photos. The FIRST is the visitor (and their family). "
        "The SECOND is a real place.",
        base,
        "Keep the environment recognisably the same location - a visitor should "
        "still be able to tell where it is.",
    ]
    if user_request.strip():
        parts.append(f"The visitor specifically asked for: {user_request.strip()}")
    parts += [IDENTITY_RULE, QUALITY_RULE]
    return "\n\n".join(parts)
