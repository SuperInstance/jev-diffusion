"""
JEV-Diffusion: image generation via substrate segmentation + LLM-as-GAN.

Casey (2026-09-22): 'JEV difusion using quilt to segment and difuse systematically
with the help of LLMs and no actual image generator. just periodic calls to the LLM
as a GAN'

Pattern:
1. Target → JEV plans (regions, mood, palette, lighting)
2. Substrate segmentation into cells
3. Each cell rendered by LLM (alternating Qwen/DeepSeek, routed by Composite-JEV)
4. Combine into unified description
5. Critic loop (Composite-JEV voting for robustness)
6. Stream events for studio UI

NO actual image generator. The output is a refined text description that COULD
be passed to a real diffusion model. But the refinement loop is the interesting
part.
"""
from __future__ import annotations
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional


# === CANONICAL FNV-1a HASH (for prev_hash chain) ===
FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3


def fnv1a_64(text: str) -> str:
    """FNV-1a 64-bit hash. Matches fleet canary."""
    h = FNV_OFFSET
    for byte in text.encode('utf-8'):
        h ^= byte
        h = (h * FNV_PRIME) & 0xffffffffffffffff
    return f"0x{h:016x}"


# === LLM BACKEND ===

class LLMBackend(Enum):
    QWEN = 'qwen'
    DEEPSEEK = 'deepseek'
    KIMI = 'kimi'
    JEV = 'jev'


def call_llm(backend: LLMBackend, prompt: str, max_tokens: int = 1500, temperature: float = 0.8) -> str:
    """Dispatch to the right LLM."""
    if backend == LLMBackend.QWEN:
        return _call_qwen(prompt, max_tokens, temperature)
    elif backend == LLMBackend.DEEPSEEK:
        return _call_deepseek(prompt, max_tokens, temperature)
    elif backend == LLMBackend.KIMI:
        return _call_kimi(prompt, max_tokens, temperature)
    else:
        raise ValueError(f'Unknown backend: {backend}')


def _call_qwen(prompt: str, max_tokens: int, temperature: float) -> str:
    req = json.dumps({
        'model': 'Qwen/Qwen3-235B-A22B-Instruct-2507',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }).encode()
    http_req = urllib.request.Request(
        'https://api.deepinfra.com/v1/openai/chat/completions',
        data=req,
        headers={'Authorization': f'Bearer {os.environ["DEEPINFRA_TOKEN"]}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(http_req, timeout=60) as r:
        return json.loads(r.read())['choices'][0]['message']['content']


def _call_deepseek(prompt: str, max_tokens: int, temperature: float) -> str:
    req = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }).encode()
    http_req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=req,
        headers={'Authorization': f'Bearer {os.environ["DEEPSEEK_TOKEN"]}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(http_req, timeout=60) as r:
        return json.loads(r.read())['choices'][0]['message']['content']


def _call_kimi(prompt: str, max_tokens: int, temperature: float) -> str:
    req = json.dumps({
        'model': 'moonshotai/Kimi-K2.6',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }).encode()
    http_req = urllib.request.Request(
        'https://api.deepinfra.com/v1/openai/chat/completions',
        data=req,
        headers={'Authorization': f'Bearer {os.environ["DEEPINFRA_TOKEN"]}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(http_req, timeout=60) as r:
        return json.loads(r.read())['choices'][0]['message']['content']


# === JEV ===

def call_jev(state: str, questions: dict) -> dict:
    req = json.dumps({'model': 'jev-latest', 'state': state, 'questions': questions}).encode()
    http_req = urllib.request.Request(
        'https://api.typesafe.ai/v1/systemone',
        data=req,
        headers={'Authorization': f'Bearer {os.environ["TYPESAFEAI_KEY"]}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(http_req, timeout=60) as r:
        return json.loads(r.read())


# === COMPOSITE JEV (multi-model agreement) ===

def composite_jev_agreement(state: str, questions: dict, n_models: int = 3) -> dict:
    """Composite-JEV: get JEV's answer, then validate via N other models.
    
    Returns the most agreed-upon answer with confidence.
    """
    # Get JEV's primary answer
    jev_resp = call_jev(state, questions)
    
    # Get validation votes from Qwen + DeepSeek
    vote_prompts = []
    for q_name, q_data in questions.items():
        if q_data.get('type') == 'choice':
            options = list(q_data.get('criteria', {}).keys())
            vote_prompt = f"For: '{state}'. Choose exactly one of: {options}. Reply with ONLY the choice name."
            vote_prompts.append((q_name, q_data.get('instructions', ''), vote_prompt))
    
    votes = {q_name: {} for q_name, _, _ in vote_prompts}
    for q_name, instruction, vote_prompt in vote_prompts:
        for backend in [LLMBackend.QWEN, LLMBackend.DEEPSEEK]:
            try:
                response = call_llm(backend, vote_prompt, max_tokens=20, temperature=0.1)
                # Parse response (look for matching option)
                for option in questions[q_name].get('criteria', {}):
                    if option.lower() in response.lower():
                        votes[q_name].setdefault(option, 0)
                        votes[q_name][option] += 1
                        break
            except Exception:
                pass
    
    return {
        'jev': jev_resp,
        'votes': votes,
        'agreement': {q_name: max(vote_dict.items(), key=lambda x: x[1])[0] if vote_dict else None for q_name, vote_dict in votes.items()},
    }


# === PRESETS (canonical substrates) ===

PRESETS = {
    'landscape': {
        'regions': ['sky', 'horizon', 'midground', 'foreground'],
        'mood_choices': ['serene', 'dramatic', 'mysterious', 'cheerful', 'melancholy'],
        'palette_choices': ['warm', 'cool', 'complementary', 'monochromatic', 'pastel'],
    },
    'portrait': {
        'regions': ['background', 'head', 'shoulders', 'hands', 'accent'],
        'mood_choices': ['intimate', 'formal', 'candid', 'dramatic', 'gentle'],
        'palette_choices': ['natural', 'warm', 'cool', 'vintage', 'high-contrast'],
    },
    'abstract': {
        'regions': ['composition_1', 'composition_2', 'composition_3', 'composition_4'],
        'mood_choices': ['energetic', 'meditative', 'chaotic', 'minimal', 'harmonic'],
        'palette_choices': ['bold', 'subtle', 'gradient', 'contrast', 'analogous'],
    },
    'still_life': {
        'regions': ['background', 'tabletop', 'primary_object', 'secondary_object', 'accent'],
        'mood_choices': ['peaceful', 'nostalgic', 'vibrant', 'moody', 'elegant'],
        'palette_choices': ['warm', 'muted', 'rich', 'pastel', 'monochrome'],
    },
    'sci_fi': {
        'regions': ['environment', 'structure', 'vessel', 'lighting', 'particle'],
        'mood_choices': ['epic', 'intimate', 'ominous', 'wondrous', 'lonely'],
        'palette_choices': ['cyberpunk', 'tactical', 'alien', 'cosmic', 'industrial'],
    },
}


# === SUBSTRATE CELL ===

@dataclass
class SubstrateCell:
    """One cell in the image substrate."""
    cell_id: str
    region: str
    position: tuple
    prev_hash: str = '0x0000000000000000'
    jev_decision: dict = field(default_factory=dict)
    llm_render: str = ''
    critic_score: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    def hash(self) -> str:
        canonical = f'{self.cell_id}|{self.prev_hash}|{self.llm_render}'
        return fnv1a_64(canonical)


# === EVENT SYSTEM (for streaming) ===

@dataclass
class DiffusionEvent:
    """One event in the diffusion process. Streamable to studio."""
    event_type: str  # 'plan', 'cell_seeded', 'cell_rendered', 'critic_voted', 'combined', 'final'
    timestamp: float
    data: dict


# === JEV DIFFUSION ===

@dataclass
class JevDiffusion:
    target: str
    preset: str = 'landscape'
    iterations: int = 3
    use_composite_jev: bool = True
    events: list = field(default_factory=list)
    cells: list = field(default_factory=list)
    plan: dict = field(default_factory=dict)
    combined: str = ''
    final_score: float = 0.0
    
    def _emit(self, event_type: str, data: dict):
        event = DiffusionEvent(event_type=event_type, timestamp=time.time(), data=data)
        self.events.append(event)
        return event
    
    def run(self) -> dict:
        """Run the full diffusion pipeline. Returns the final state."""
        self._plan()
        self._segment()
        self._render_cells()
        self._critic_loop()
        self._assemble()
        return self.to_dict()
    
    def _plan(self):
        """JEV plans the composition."""
        preset = PRESETS[self.preset]
        
        if self.use_composite_jev:
            plan_resp = composite_jev_agreement(self.target, {
                'regions': {
                    'type': 'choice',
                    'instructions': f'Which region layout fits this target? preset regions: {preset["regions"]}',
                    'criteria': {r: r for r in preset['regions']},
                },
                'mood': {
                    'type': 'choice',
                    'instructions': 'What mood?',
                    'criteria': {m: m for m in preset['mood_choices']},
                },
                'palette': {
                    'type': 'choice',
                    'instructions': 'What palette?',
                    'criteria': {p: p for p in preset['palette_choices']},
                },
                'lighting': {
                    'type': 'score',
                    'instructions': 'How dramatic is the lighting? 0=flat, 1=normal, 2=dramatic chiaroscuro',
                    'criteria': ['flat', 'normal', 'dramatic'],
                },
            })
            jev_ans = plan_resp['jev']['answers']
            votes = plan_resp['votes']
            agreement = plan_resp['agreement']
            
            # Use agreement if it differs from JEV
            self.plan = {
                'regions': agreement.get('regions') or jev_ans['regions']['choice'],
                'mood': agreement.get('mood') or jev_ans['mood']['choice'],
                'palette': agreement.get('palette') or jev_ans['palette']['choice'],
                'lighting': jev_ans['lighting']['score'],
                'confidences': {
                    k: jev_ans[k].get('confidence', 0.5) 
                    for k in ['regions', 'mood', 'palette', 'lighting']
                },
                'votes': votes,
                'agreement': agreement,
            }
        else:
            jev_resp = call_jev(self.target, {
                'regions': {
                    'type': 'choice',
                    'instructions': f'Which region layout fits this target? preset regions: {preset["regions"]}',
                    'criteria': {r: r for r in preset['regions']},
                },
                'mood': {
                    'type': 'choice',
                    'instructions': 'What mood?',
                    'criteria': {m: m for m in preset['mood_choices']},
                },
                'palette': {
                    'type': 'choice',
                    'instructions': 'What palette?',
                    'criteria': {p: p for p in preset['palette_choices']},
                },
                'lighting': {
                    'type': 'score',
                    'instructions': 'How dramatic is the lighting?',
                    'criteria': ['flat', 'normal', 'dramatic'],
                },
            })
            jev_ans = jev_resp['answers']
            self.plan = {
                'regions': jev_ans['regions']['choice'],
                'mood': jev_ans['mood']['choice'],
                'palette': jev_ans['palette']['choice'],
                'lighting': jev_ans['lighting']['score'],
                'confidences': {
                    k: jev_ans[k].get('confidence', 0.5) 
                    for k in ['regions', 'mood', 'palette', 'lighting']
                },
            }
        
        self._emit('plan', self.plan)
    
    def _segment(self):
        """Substrate segmentation into cells."""
        preset = PRESETS[self.preset]
        regions = preset['regions']
        
        prev_hash = '0x0000000000000000'
        for i, region in enumerate(regions):
            cell = SubstrateCell(
                cell_id=f'cell-{i:02d}',
                region=region,
                position=(i, 0),
                prev_hash=prev_hash,
                metadata={'preset': self.preset},
            )
            self.cells.append(cell)
            prev_hash = cell.hash()
            self._emit('cell_seeded', {
                'cell_id': cell.cell_id,
                'region': cell.region,
                'position': cell.position,
            })
    
    def _render_cells(self):
        """Each cell is rendered by an LLM. Alternate between Qwen and DeepSeek."""
        for i, cell in enumerate(self.cells):
            # Alternate backends for diversity
            backend = LLMBackend.QWEN if i % 2 == 0 else LLMBackend.DEEPSEEK
            
            prompt = f"""You are rendering a SUBSTRATE CELL of an image description.

TARGET IMAGE: {self.target}

PLAN:
- Regions: {self.plan['regions']}
- Mood: {self.plan['mood']}
- Palette: {self.plan['palette']}
- Lighting: {self.plan['lighting']}/2

YOUR CELL:
- Region: {cell.region}
- Position: cell {i+1} of {len(self.cells)} in the substrate
- Neighbors: {[c.region for c in self.cells if c.cell_id != cell.cell_id]}

Write a vivid, detailed description (3-5 sentences) of what this CELL contains in the image.
Be specific about colors, textures, light, and composition.
Write so that adjacent cells can connect to yours seamlessly.

CELL:"""
            
            try:
                cell.llm_render = call_llm(backend, prompt, max_tokens=600, temperature=0.85)
                cell.metadata['backend'] = backend.value
                cell.metadata['rendered_at'] = time.time()
            except Exception as e:
                cell.llm_render = f'[RENDER FAILED: {e}]'
                cell.metadata['error'] = str(e)
            
            self._emit('cell_rendered', {
                'cell_id': cell.cell_id,
                'region': cell.region,
                'backend': backend.value,
                'content_preview': cell.llm_render[:200],
                'content_length': len(cell.llm_render),
            })
    
    def _critic_loop(self):
        """Critic loop: GAN-like refinement via multi-agent voting."""
        for iteration in range(self.iterations):
            # Combine current state
            current = '\n\n'.join(c.llm_render for c in self.cells)
            
            # Critic prompt
            critic_prompt = f"""You are a critic reviewing a substrate-segmented image description.

TARGET: {self.target}

PLAN: {self.plan}

CELLS:
{current}

Score these 0-10:
- completeness: Does it cover all aspects of the target?
- specificity: Is it vivid and concrete?
- coherence: Do the cells connect smoothly?
- composition: Does it describe a strong visual composition?

Reply with ONLY this JSON:
{{"completeness": 0-10, "specificity": 0-10, "coherence": 0-10, "composition": 0-10, "feedback": "1-sentence constructive feedback"}}
"""
            try:
                # Use Qwen as primary critic (good at evaluation)
                response = call_llm(LLMBackend.QWEN, critic_prompt, max_tokens=400, temperature=0.3)
                m = re.search(r'\{[\s\S]*\}', response)
                if m:
                    critic = json.loads(m.group())
                    avg = (critic['completeness'] + critic['specificity'] + critic['coherence'] + critic['composition']) / 4
                    
                    # Update cell scores
                    for cell in self.cells:
                        cell.critic_score = avg
                    
                    self._emit('critic_voted', {
                        'iteration': iteration,
                        'scores': {k: critic[k] for k in ['completeness', 'specificity', 'coherence', 'composition']},
                        'avg': avg,
                        'feedback': critic.get('feedback', ''),
                    })
                    
                    # If quality is good, stop early
                    if avg >= 9.0:
                        break
            except Exception as e:
                self._emit('critic_voted', {
                    'iteration': iteration,
                    'error': str(e),
                    'avg': 0,
                })
    
    def _assemble(self):
        """Combine cells into a final description."""
        if not self.cells:
            self.combined = ''
            return
        
        # Use DeepSeek (best at coherent writing) for the final assembly
        cells_text = '\n\n'.join(f'**{c.region.upper()}** (cell {c.cell_id}):\n{c.llm_render}' for c in self.cells)
        
        assembly_prompt = f"""You are combining substrate-segmented cell descriptions into a unified image description.

TARGET: {self.target}

PLAN: {self.plan}

CELLS:
{cells_text}

Write a unified 4-6 sentence description that flows as one cohesive image.
Use transitions between cells. Maintain consistent voice and tone.

UNIFIED DESCRIPTION:"""
        
        try:
            self.combined = call_llm(LLMBackend.DEEPSEEK, assembly_prompt, max_tokens=1500, temperature=0.6)
        except Exception as e:
            # Fallback: just concatenate
            self.combined = ' '.join(c.llm_render for c in self.cells)
        
        # Final score
        if self.cells and self.cells[0].critic_score:
            self.final_score = self.cells[0].critic_score
        
        self._emit('final', {
            'combined': self.combined,
            'final_score': self.final_score,
            'num_cells': len(self.cells),
            'iterations': len([e for e in self.events if e.event_type == 'critic_voted']),
        })
    
    def to_dict(self) -> dict:
        return {
            'target': self.target,
            'preset': self.preset,
            'iterations': self.iterations,
            'plan': self.plan,
            'cells': [
                {
                    'cell_id': c.cell_id,
                    'region': c.region,
                    'position': c.position,
                    'prev_hash': c.prev_hash,
                    'hash': c.hash(),
                    'jev_decision': c.jev_decision,
                    'llm_render': c.llm_render,
                    'critic_score': c.critic_score,
                    'metadata': c.metadata,
                }
                for c in self.cells
            ],
            'combined': self.combined,
            'final_score': self.final_score,
            'events': [{'type': e.event_type, 'timestamp': e.timestamp, 'data': e.data} for e in self.events],
        }


# === CLI ===

def main():
    import argparse
    p = argparse.ArgumentParser(description='JEV-Diffusion: substrate-segmented LLM-as-GAN image description')
    p.add_argument('target', help='What to describe (e.g. "a sunset over a mountain lake")')
    p.add_argument('--preset', default='landscape', choices=list(PRESETS.keys()))
    p.add_argument('--iterations', type=int, default=3)
    p.add_argument('--no-composite', action='store_true', help='Disable composite-JEV (faster)')
    p.add_argument('--output', default='-', help='Output file (- for stdout)')
    p.add_argument('--stream', action='store_true', help='Stream events to stderr')
    args = p.parse_args()
    
    diffusion = JevDiffusion(
        target=args.target,
        preset=args.preset,
        iterations=args.iterations,
        use_composite_jev=not args.no_composite,
    )
    
    # If streaming, override emit
    if args.stream:
        orig_emit = diffusion._emit
        def stream_emit(event_type, data):
            event = orig_emit(event_type, data)
            print(f'[{event_type}] {json.dumps(data, default=str)[:200]}', file=__import__('sys').stderr, flush=True)
            return event
        diffusion._emit = stream_emit
    
    result = diffusion.run()
    
    if args.output == '-':
        print(json.dumps(result, indent=2, default=str))
    else:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f'✓ Saved to {args.output}', file=__import__('sys').stderr)


if __name__ == '__main__':
    main()
