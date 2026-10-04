# Masked-chibi YouTube pipeline (local, Veo via Gemini API)

Generate the character's video clips programmatically on your own machine,
with the locked design grounding every call.

## Setup

```bash
cd pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ffmpeg must be installed:  brew install ffmpeg   (macOS)

cp .env.example .env   # then add your Gemini API key from https://aistudio.google.com
mkdir -p refs
# copy the locked references in:
cp ../canonical-reference.webp ../mask-closeup.png ../tattoos-closeup.png refs/
cp ../cyndi-reference.jpg ../cyndi-face-closeup.png refs/   # only needed for dog scenes
```

## Providers: Veo or Kling

Two generation backends, same scenes.json format, same verify/assemble steps:

| | Veo (`generate_clips.py`) | Kling (`generate_clips_kling.py`) |
|---|---|---|
| Model | `veo-3.1-generate-preview` (Gemini API) | `fal-ai/kling-video/o3/standard/reference-to-video` (fal.ai) |
| Character lock | reference images + spec text | native `elements` (`@Element1` = character, `@Element2` = Cyndi) |
| Key | `GEMINI_API_KEY` | `FAL_KEY` |
| Rough cost | ~$0.75/s → ~$630 full video | ~$0.10/s → ~$105 full video |
| Notes | best realism; SDK model IDs churn | best motion; pay-per-clip, no commitment |

```bash
# Kling route (same scenes.json):
python generate_clips_kling.py --scenes scenes.json --out clips_kling/ --dry-run
python generate_clips_kling.py --scenes scenes.json --out clips_kling/
```
Then `verify_clips.py --clips clips_kling/ --review review_kling/` and
`assemble.py` exactly as above. The `elements` mechanism is Kling's native
character lock — the reference images ride as an image set and the prompt
addresses them as `@Element1`/`@Element2`.

## Workflow

1. **Write scenes** — `scenes.json`, a list of `{id, prompt, dog?, duration_seconds?}`.
   See `scenes.example.json`. One scene ≈ one 8s clip ≈ ~20 words of narration.
   Put `{"dog": true}` on any scene where Cyndi appears.
2. **Estimate cost** — `python generate_clips.py --scenes scenes.json --out clips/ --dry-run`
   (Veo 3.1 ≈ $0.75/s at time of writing — **verify current pricing**; the full
   14-min video is ~105 clips ≈ $630 before drift retries.)
3. **Generate** — `python generate_clips.py --scenes scenes.json --out clips/`
   Skips scenes already done (resume-safe via `clips/manifest.json`).
   Redo one: `--only <id> --force`.
4. **Verify** — `python verify_clips.py --clips clips/ --review review/`
   and eyeball every contact sheet (mask shape, king+queen tattoos, outfit,
   feet, Cyndi's bandana). Regenerate drifted scenes with `--only <id> --force`.
   Automated drift detection isn't reliable — this human pass is the system.
5. **Voiceover** — produce narration audio yourself (ElevenLabs, Google Cloud
   TTS, or any studio). One mp3 per chapter, e.g. `ch1-vo.mp3`.
6. **Assemble** — list clips in order in `ch1_order.txt`, then
   `python assemble.py --order ch1_order.txt --voiceover ch1-vo.mp3 --out ch1.mp4`

## How character consistency works here

Every `generate_videos` call sends the locked reference images
(`reference_images=[character, mask closeup, tattoos closeup, (+ Cyndi)]`)
**and** appends the character spec from `config.py` to the prompt. This is the
same grounding the chat pipeline uses — it's what stops the mask morphing and
the tattoos flipping. `generate_audio=False` is set deliberately: Veo's
synthesized soundtracks are unreliable (stray voices), so clips are silent and
the voiceover is laid on in `assemble.py`.

## Notes / gotchas

- Google renames the preview model IDs every few months. If calls fail with
  "model not found", check https://ai.google.dev/gemini-api/docs/video and
  update `MODEL` in `config.py`.
- Generated videos live on Google's servers ~2 days; the script downloads
  immediately, so this doesn't matter.
- `720p` keeps costs and iteration speed sane; switch to `1080p` in
  `config.py` for the final render of hero scenes.
- Keep a scene's prompt to one clear action. Two actions per clip is where
  drift and muddled motion creep in.
