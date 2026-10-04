#!/usr/bin/env python3
"""Extract review frames from generated clips so a human can check character
consistency (mask shape, tattoo pairing) before assembly.

Automated drift detection isn't reliable — your eyes are the verifier, same
as in the chat pipeline.

Usage:
    python verify_clips.py --clips clips/ --review review/
Then open review/ and look at every contact sheet. Regenerate drifted scenes
with:  python generate_clips.py --scenes scenes.json --out clips/ --only <id> --force
"""
import argparse
import subprocess
from pathlib import Path

N_FRAMES = 3  # beginning / middle / end


def contact_sheet(clip: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # 3 frames side-by-side, scaled down for quick review
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
         "-vf", f"select='eq(n\\,10)+eq(n\\,90)+eq(n\\,170)',scale=320:-1,tile=3x1",
         "-frames:v", "1", str(out)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True)
    ap.add_argument("--review", required=True)
    args = ap.parse_args()
    clips = sorted(Path(args.clips).glob("*.mp4"))
    if not clips:
        raise SystemExit(f"No mp4s in {args.clips}")
    for clip in clips:
        out = Path(args.review) / f"{clip.stem}_review.jpg"
        contact_sheet(clip, out)
        print(f"{clip.name} -> {out}")
    print("\nChecklist per sheet:")
    print("  [ ] mask = matte black OVAL, two ROUND eye holes (no morphing)")
    print("  [ ] neck tattoos = KING one side, QUEEN the other (never two of one)")
    print("  [ ] outfit: black cardigan / white tee / cargo pants / Sambas")
    print("  [ ] feet point forward, not splayed")
    print("  [ ] Cyndi (if present) = tan, upright ears, red/white bandana, photorealistic")


if __name__ == "__main__":
    main()
