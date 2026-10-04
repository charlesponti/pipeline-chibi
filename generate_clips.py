#!/usr/bin/env python3
"""Generate Veo clips for every scene in scenes.json, grounded on the locked
character references.

Usage:
    python generate_clips.py --scenes scenes.json --out clips/
    python generate_clips.py --scenes scenes.json --out clips/ --only ch1_s3
    python generate_clips.py --scenes scenes.json --out clips/ --force   # redo existing
    python generate_clips.py --scenes scenes.json --dry-run               # cost estimate only

State is tracked in <out>/manifest.json so interrupted runs resume cleanly.
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

import config

log = logging.getLogger("generate_clips")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REF_FILES = {
    "character": "canonical-reference.webp",
    "mask": "mask-closeup.png",
    "tattoos": "tattoos-closeup.png",
    "dog": "cyndi-reference.jpg",
    "dog_face": "cyndi-face-closeup.png",
}


def build_client() -> genai.Client:
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return genai.Client(api_key=key)


def build_refs(scene: dict) -> list:
    names = ["character", "mask", "tattoos"]
    if scene.get("dog"):
        names += ["dog", "dog_face"]
    refs = []
    for n in names:
        p = config.REF_DIR / REF_FILES[n]
        if not p.exists():
            sys.exit(f"Missing reference image: {p} (see README step 2)")
        img = types.Image.from_file(location=str(p))
        refs.append(types.VideoGenerationReferenceImage(image=img, reference_type="asset"))
    return refs


def build_prompt(scene: dict) -> str:
    parts = [
        scene["prompt"],
        "Character lock — match exactly:\n" + config.CHARACTER_SPEC,
    ]
    if scene.get("dog"):
        parts.append("Dog lock — match exactly:\n" + config.CYNDI_SPEC)
    return "\n\n".join(parts)


def generate_one(client: genai.Client, scene: dict, out_path: Path) -> None:
    refs = build_refs(scene)
    duration = scene.get("duration_seconds", config.DURATION_SECONDS)
    log.info("Generating %s (%ss)...", scene["id"], duration)
    op = client.models.generate_videos(
        model=config.MODEL,
        prompt=build_prompt(scene),
        config=types.GenerateVideosConfig(
            aspect_ratio=config.ASPECT_RATIO,
            resolution=config.RESOLUTION,
            duration_seconds=duration,
            number_of_videos=1,
            generate_audio=False,  # we lay our own voiceover; generated audio is unreliable
            negative_prompt="speech, talking, singing, voices, text overlay, "
                            "subtitles, watermark, logo, extra limbs, deformed hands",
            reference_images=refs,
            seed=scene.get("seed"),
        ),
    )
    while not op.done:
        time.sleep(config.POLL_INTERVAL_S)
        op = client.operations.get(op)
    if op.error:
        raise RuntimeError(f"Veo error: {op.error}")
    video = op.response.generated_videos[0].video
    out_path.parent.mkdir(parents=True, exist_ok=True)
    video.save(str(out_path))  # SDK-provided download; falls back below
    log.info("Saved %s", out_path)


def estimate_cost(scenes: list) -> float:
    total_s = sum(s.get("duration_seconds", config.DURATION_SECONDS) for s in scenes)
    return total_s * config.COST_PER_SECOND_USD


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True, help="scenes.json path")
    ap.add_argument("--out", required=True, help="output dir for clips")
    ap.add_argument("--only", help="only generate this scene id")
    ap.add_argument("--force", action="store_true", help="regenerate even if output exists")
    ap.add_argument("--dry-run", action="store_true", help="print cost estimate and exit")
    ap.add_argument("--yes", action="store_true", help="skip the cost confirmation prompt")
    args = ap.parse_args()

    scenes = json.loads(Path(args.scenes).read_text())
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]
        if not scenes:
            sys.exit(f"No scene with id {args.only!r}")

    cost = estimate_cost(scenes)
    log.info("%d scenes, estimated cost: $%.2f (verify pricing!)", len(scenes), cost)
    if args.dry_run:
        return
    if not args.yes:
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans != "y":
            sys.exit("Aborted.")

    client = build_client()
    out_dir = Path(args.out)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for scene in scenes:
        out_path = out_dir / f"{scene['id']}.mp4"
        if out_path.exists() and not args.force:
            log.info("Skipping %s (exists, use --force to redo)", scene["id"])
            continue
        try:
            generate_one(client, scene, out_path)
            manifest[scene["id"]] = {"file": str(out_path), "status": "ok",
                                     "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        except Exception as e:  # noqa: BLE001 - record and continue; retry with --only
            log.error("FAILED %s: %s", scene["id"], e)
            manifest[scene["id"]] = {"status": "failed", "error": str(e)}
        manifest_path.write_text(json.dumps(manifest, indent=2))

    failed = [k for k, v in manifest.items() if v.get("status") == "failed"]
    log.info("Done. %d ok, %d failed.", len(manifest) - len(failed), len(failed))
    if failed:
        log.info("Retry with: --only <id>")


if __name__ == "__main__":
    main()
