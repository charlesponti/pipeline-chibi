"""Config for the Kling adapter (fal.ai). Mirrors config.py's interface so the
rest of the pipeline (verify_clips.py, assemble.py) works unchanged.

Why this endpoint: fal-ai/kling-video/o3/standard/reference-to-video is
purpose-built for reference-driven generation — no start frame required,
generate_audio defaults to false, and `elements` is Kling's native
character-lock: pass the character as an image set, address it as @Element1
in the prompt.
"""
from pathlib import Path

# --- Model & render settings -------------------------------------------------
MODEL = "fal-ai/kling-video/o3/standard/reference-to-video"
ASPECT_RATIO = "16:9"        # YouTube long-form ("16:9" | "9:16" | "1:1")
DURATION_SECONDS = 10        # 3..15
GENERATE_AUDIO = False       # we lay our own voiceover; keep silent

# --- Cost control ------------------------------------------------------------
# Conservative estimate for o3/standard at time of writing; VERIFY current
# pricing at fal.ai before a big run. (Kling v3.0-std lists $0.084/s.)
# Full video ≈ 105 clips x 10s x $0.10 ≈ $105 before drift retries.
COST_PER_SECOND_USD = 0.10

# --- Paths -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
REF_DIR = BASE_DIR / "refs"   # same locked references as the Veo pipeline

# --- Character lock ----------------------------------------------------------
# Appended to every prompt alongside the @ElementN references. Keep in sync
# with character-bible.md.
CHARACTER_SPEC = """\
3D chibi cartoon boy, soft Pixar-like render.
- Hair: voluminous black curly hair, medium length, covers forehead and ears.
- Mask: matte black OVAL mask covering the full face. Two ROUND symmetric eye
  holes. Small dark strap buckles at both sides and one at top center.
  No mouth, no nose detail. NEVER change the mask shape.
  Real eyes NEVER visible; eye holes are dark empty voids.
- Neck tattoos: TWO portraits, always this pairing — a crowned KING (bearded
  man in profile) on one side of the neck, a crowned QUEEN (woman in profile)
  on the other side. Never two kings, never two queens.
- Outfit: black knit button cardigan (patch pockets) over plain white crew
  t-shirt; black cargo pants with side flap pockets; black Adidas Samba
  sneakers (white side stripes, gum-brown soles, small blue heel tab).
- Feet point forward, never splayed outward."""

CYNDI_SPEC = """\
Cyndi the dog, PHOTOREALISTIC (never cartoon, never stylized).
- Medium-large mixed breed, lean athletic build, tan/golden short coat,
  white chest patch, white-tipped front paws.
- Upright pointed ears, black muzzle and nose, dark expressive eyes.
- Always wears her red-and-white patterned bandana around the neck."""
