---
canon: 1
name: jev-diffusion
mission: "Image generation via substrate segmentation + LLM-as-GAN. The cell is the irreducible unit. The model is the renderer."
state: working
family: applications
vessel: SuperInstance
born_from: [casey-2026-09-22, jev_revelation, substrate_cell_doctrine]
canonical_docs: [README.md, DOCTRINE.md, studio/index.html]
ledger: git-log
verified: 2026-09-22
---

# jev-diffusion

> Substrate-segmented image description. No actual image generator. Just JEV + LLMs as a GAN.

## The doctrine

Image generation has been GPU-bound for too long. LLMs can describe images
beautifully — let them.

The pattern:
1. JEV plans composition (regions, mood, palette, lighting)
2. Substrate segments into cells
3. Each cell rendered by LLM (Qwen/DeepSeek alternately, or composite-JEV routed)
4. Critic loop scores, refines
5. Unify into 4-6 sentence description

The output is TEXT — a refined description that could be fed to any image generator.
But the refinement loop is where the interesting work happens.

## Studio

`studio/index.html` — full interactive studio with prompt input, live cell rendering,
critic visualization, gallery of examples, and copy/share/export actions.

## Status

- [x] Refactored engine with Composite-JEV + presets + prev_hash + streaming
- [x] 13/13 unit tests pass
- [x] Real demo scored 9.5/10
- [x] Studio HTML/JS/CSS
- [x] Documentation page
- [x] Gallery with 6 pre-rendered examples

## See also

- `text_diffusion/` — mitosis for long descriptions
- `composite_jev/` — multi-model voting
- `motif_quilt/` — agents that operate on cells
- `studio/docs.html` — full methodology
