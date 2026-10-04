#!/usr/bin/env python3
"""Generate Kling clips for every scene in scenes.json, with the locked
character passed as native `elements` (@Element1 = character, @Element2 = Cyndi).

Usage:
    python generate_clips_kling.py --scenes scenes.json --out clips_kling/
    python generate_clips_kling.py --scenes scenes.json --out clips_kling/ --only ch1_s3
    python generate_clips_kling.py --scenes scenes.json --out clips_kling/ --force
    python generate_clips_kling.py --scenes scenes.json --dry-run

Same scenes.json format as generate_clips.py. State in <out>/manifest.json.
Needs FAL_KEY in .env (get one at https://fal.ai).
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

import fal_client

import config_kling as cfg

log = logging.getLogger("generate_clips_kling")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REF_FILES = {
    "character": "canonical-reference.webp",
    "mask": "mask-closeup.png",
    "tattoos": "tattoos-closeup.png",
    "dog": "cyndi-reference.jpg",
    "dog_face": "cyndi-face-closeup.png",
}


def check_key() -> None:
    load_dotenv()
    if not os.environ.get("FAL_KEY"):
        sys.exit("FAL_KEY is not set. Copy .env.example to .env and add your fal.ai key.")


def upload_refs(manifest: dict) -> dict:
    """Upload each locked reference once; cache URLs in the manifest."""
    uploads = manifest.get("_uploads", {})
    for name, fname in REF_FILES.items():
        if name in uploads:
            continue
        p = cfg.REF_DIR / fname
        if not p.exists():
            sys.exit(f"Missing reference image: {p} (see README step 2)")
        log.info("Uploading %s...", fname)
        uploads[name] = fal_client.upload_file(str(p))
    manifest["_uploads"] = uploads
    return uploads


def build_elements(uploads: dict, scene: dict) -> list:
    elements = [{
        "frontal_image_url": uploads["character"],
        "reference_image_urls": [uploads["mask"], uploads["tattoos"]],
    }]
    if scene.get("dog"):
        elements.append({
            "frontal_image_url": uploads["dog"],
            "reference_image_urls": [uploads["dog_face"]],
        })
    return elements


def build_prompt(scene: dict) -> str:
    refs = "@Element1"
    if scene.get("dog"):
        refs += " and @Element2"
    parts = [f"{refs}: {scene['prompt']}",
             "Character lock — match exactly:\n" + cfg.CHARACTER_SPEC]
    if scene.get("dog"):
        parts.append("Dog lock — match exactly:\n" + cfg.CYNDI_SPEC)
    return "\n\n".join(parts)


def generate_one(uploads: dict, scene: dict, out_path: Path) -> None:
    duration = scene.get("duration_seconds", cfg.DURATION_SECONDS)
    if not 3 <= duration <= 15:
        raise ValueError(f"duration_seconds must be 3..15, got {duration}")
    log.info("Generating %s (%ss, %s)...", scene["id"], duration, cfg.MODEL)
    result = fal_client.subscribe(
        cfg.MODEL,
        arguments={
            "prompt": build_prompt(scene),
            "elements": build_elements(uploads, scene),
            "duration": str(duration),
            "aspect_ratio": cfg.ASPECT_RATIO,
            "generate_audio": cfg.GENERATE_AUDIO,
            "negative_prompt": "speech, talking, singing, voices, text overlay, "
                               "subtitles, watermark, logo, extra limbs, deformed hands, "
                               "real human eyes",
        },
        with_logs=False,
    )
    video_url = result["video"]["url"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(video_url, timeout=120)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    log.info("Saved %s (%.1f MB)", out_path, len(r.content) / 1e6)


def estimate_cost(scenes: list) -> float:
    total_s = sum(s.get("duration_seconds", cfg.DURATION_SECONDS) for s in scenes)
    return total_s * cfg.COST_PER_SECOND_USD


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="only generate this scene id")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
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
        if input("Proceed? [y/N] ").strip().lower() != "y":
            sys.exit("Aborted.")

    check_key()
    out_dir = Path(args.out)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    uploads = upload_refs(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2))

    for scene in scenes:
        out_path = out_dir / f"{scene['id']}.mp4"
        if out_path.exists() and not args.force:
            log.info("Skipping %s (exists, use --force to redo)", scene["id"])
            continue
        try:
            generate_one(uploads, scene, out_path)
            manifest[scene["id"]] = {"file": str(out_path), "status": "ok",
                                     "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        except Exception as e:  # noqa: BLE001 - record and continue; retry with --only
            log.error("FAILED %s: %s", scene["id"], e)
            manifest[scene["id"]] = {"status": "failed", "error": str(e)}
        manifest_path.write_text(json.dumps(manifest, indent=2))

    failed = [k for k, v in manifest.items()
              if k != "_uploads" and v.get("status") == "failed"]
    log.info("Done. %d ok, %d failed.", len(manifest) - len(failed) - 1, len(failed))
    if failed:
        log.info("Retry with: --only <id>")


if __name__ == "__main__":
    main()
