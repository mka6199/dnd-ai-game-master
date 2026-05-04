"""Innovation features: text-to-speech narration and AI image generation.

These are the "creative add-ons" for the rubric's Innovation section.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from gtts import gTTS

from game.llm import generate_image as _llm_generate_image


AUDIO_DIR = Path("generated_audio")
IMAGE_DIR = Path("generated_images")


def synthesize_speech(text: str, lang: str = "en", slow: bool = False) -> str:
    """Convert narration text to an MP3 file using gTTS (free, no API key).

    Returns the path to the generated audio file.
    """
    AUDIO_DIR.mkdir(exist_ok=True)
    if not text.strip():
        raise ValueError("Cannot synthesize empty text.")
    # gTTS chokes on very long inputs; truncate to ~5000 chars to be safe
    text = text[:4900]
    out_path = AUDIO_DIR / f"narration-{uuid.uuid4().hex[:8]}.mp3"
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(out_path))
    return str(out_path)


def generate_npc_portrait(npc_description: str) -> str:
    """Generate an NPC portrait via DALL-E 3. Returns the image URL."""
    prompt = (
        f"A detailed fantasy character portrait of {npc_description}. "
        "Painterly digital art style, dramatic lighting, head and shoulders, "
        "rich colors, fantasy D&D aesthetic, no text or watermarks."
    )
    return _llm_generate_image(prompt)


def generate_dungeon_map(scene_description: str) -> str:
    """Generate a dungeon/scene illustration via DALL-E 3. Returns image URL."""
    prompt = (
        f"Top-down fantasy battle map illustration of {scene_description}. "
        "Hand-drawn ink and watercolor style, atmospheric, suitable for "
        "tabletop role-playing, no text or grid."
    )
    return _llm_generate_image(prompt)
