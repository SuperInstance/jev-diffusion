# The JEV-Diffusion Doctrine

> "JEV difusion using quilt to segment and difuse systematically with the help of LLMs
> and no actual image generator. just periodic calls to the LLM as a GAN"
> — Casey, 2026-09-22

## The premise

Diffusion models are amazing. They generate images from noise. They cost $5 per
image. They use GPU clusters.

But they have a property we can exploit: they take a TEXT description and turn it
into an image. So what if we focus on the TEXT DESCRIPTION, treating the diffusion
model as an implementation detail?

The diffusion loop becomes:
- JEV plans the composition (schema-constrained, can't hallucinate)
- Substrate segments into cells
- LLMs render each cell (the "diffusion")
- Critic scores and refines (the "denoising")
- Unify into final description

**No GPU. No image generator. Just substrate + LLMs.**

## Why this matters

1. **Observable**: every cell has a hash, every iteration is logged. With real diffusion, you get noise → image and can't see the steps.

2. **Composable**: cells chain via prev_hash. You can split, merge, share, query. With real diffusion, you get a blob.

3. **Editable**: edit any cell, the rest survives (no-deletion doctrine). With real diffusion, edit = regenerate.

4. **Cheap**: $0.10 of LLM tokens vs $5 of GPU.

5. **Critic-driven**: GAN-like loop refines quality automatically. With real diffusion, you don't know when you've converged.

## The substrate cell as region

In a real image, "regions" are spatial. In JEV-Diffusion, regions are substrate cells.
Each cell has:
- `cell_id`: canonical name
- `region`: semantic role (sky, horizon, midground, foreground)
- `prev_hash`: chain link
- `llm_render`: the LLM's description
- `critic_score`: how the critic rated it

The cells are observable. The cells are traceable. The cells compose.

## The 5 stages

### Stage 1: JEV Plans

JEV makes schema-constrained decisions. Schema = the preset's regions, mood choices,
palette choices. JEV returns the chosen values + confidences. With composite-JEV,
Qwen and DeepSeek also vote.

### Stage 2: Substrate Segments

The preset defines regions (e.g., landscape = sky, horizon, midground, foreground).
Each region becomes a substrate cell. prev_hash chains them.

### Stage 3: LLMs Render

Each cell is rendered by an LLM. The LLM sees:
- The target
- The plan
- The cell's region
- The cell's neighbors

The LLM returns a 3-5 sentence description.

### Stage 4: Critic Iterates

A GAN-like critic scores the combined cells on 4 dimensions:
- completeness
- specificity
- coherence
- composition

If average ≥ 9.0, the loop stops. Otherwise, iterate up to N times.

### Stage 5: Unify

DeepSeek assembles the cells into a 4-6 sentence description. Transitions are
added, voice unified. This is the final output.

## The cross-paradigm composition

JEV-Diffusion is one piece of a larger puzzle:
- **text_diffusion**: mitosis for long descriptions (each cell can be a mitosis root)
- **composite_jev**: multi-model voting (drives composite-JEV here)
- **motif_quilt**: agents that operate on cells (can QA diffusions)
- **substrate canon**: every diffusion run creates queryable cells

The substrate is the foundation. The cell is the unit. JEV is the planner.
LLMs are the renderers. The critic is the diffusion.

## Files

- `jev_diffusion.py` — engine
- `test_jev_diffusion.py` — 13/13 tests
- `studio/index.html` — interactive studio
- `studio/docs.html` — methodology
- `CANON.md` — Layer C join declaration

## Status

- [x] Refactored engine
- [x] Studio deployed locally
- [x] Documentation
- [ ] Deploy to superinstance.dev/jev-diffusion/
- [ ] HTTP endpoint on substrate worker
- [ ] Interactive editing

## See also

- `text_diffusion/` — mitosis for long descriptions
- `composite_jev/` — multi-model voting
- `motif_quilt/` — cell-aware agents
- `motifs/` — substrate cell in many languages
