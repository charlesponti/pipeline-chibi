"""Shared config for the masked-chibi video pipeline (Veo via Gemini API)."""
from pathlib import Path

# --- Model & render settings -------------------------------------------------
# Model IDs are renamed by Google periodically ("...-preview" -> GA). If a call
# fails with "model not found", check https://ai.google.dev/gemini-api/docs/video
# and update this string.
MODEL = "veo-3.1-generate-preview"
ASPECT_RATIO = "16:9"          # YouTube long-form
RESOLUTION = "720p"           # 720p is cheaper/faster; use "1080p" for hero shots
DURATION_SECONDS = 8          # Veo 3.1 supports 4/6/8
POLL_INTERVAL_S = 20

# --- Cost control ------------------------------------------------------------
# Ballpark at time of writing; VERIFY current pricing before a big run.
# Full video ≈ 105 clips x 8s x $0.75 ≈ $630, plus ~20% for drift retries.
COST_PER_SECOND_USD = 0.75

# --- Paths -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
REF_DIR = BASE_DIR / "refs"   # <- copy the locked references here (see README)

# --- Character lock ----------------------------------------------------------
# Appended to EVERY prompt. Mirrors character-bible.md; keep the two in sync.
CHARACTER_SPEC = """\
3D chibi cartoon boy, soft Pixar-like render.
- Hair: voluminous black curly hair, medium length, covers forehead and ears.
- Mask: matte black OVAL mask covering the full face. Two ROUND symmetric eye
  holes. Small dark strap buckles at both sides and one at top center.
  No mouth, no nose detail. NEVER change the mask shape.
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
