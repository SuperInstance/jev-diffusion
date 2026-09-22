"""Tests for the refactored JEV-Diffusion engine."""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from jev_diffusion import (
    JevDiffusion, SubstrateCell, PRESETS, fnv1a_64,
    composite_jev_agreement, LLMBackend,
)


class TestFNV1a(unittest.TestCase):
    """The FNV-1a hash is our fleet canary. Same algorithm across all repos."""
    
    def test_fleet_canary(self):
        # The canonical canary: FNV-1a 64 of "café Δ 日本語"
        expected = '0x24a555471370b18d'
        self.assertEqual(fnv1a_64('café Δ 日本語'), expected)
    
    def test_hash_determinism(self):
        self.assertEqual(fnv1a_64('hello'), fnv1a_64('hello'))
    
    def test_hash_changes_with_content(self):
        self.assertNotEqual(fnv1a_64('hello'), fnv1a_64('world'))


class TestSubstrateCell(unittest.TestCase):
    def test_creation(self):
        cell = SubstrateCell(
            cell_id='cell-00',
            region='sky',
            position=(0, 0),
        )
        self.assertEqual(cell.cell_id, 'cell-00')
        self.assertEqual(cell.region, 'sky')
        self.assertEqual(cell.prev_hash, '0x0000000000000000')
    
    def test_hash_changes_with_content(self):
        c1 = SubstrateCell('c', 'r', (0,0), llm_render='hello')
        c2 = SubstrateCell('c', 'r', (0,0), llm_render='world')
        self.assertNotEqual(c1.hash(), c2.hash())
    
    def test_hash_chain(self):
        c1 = SubstrateCell('c1', 'r1', (0,0), llm_render='hello')
        c2 = SubstrateCell('c2', 'r2', (0,0), prev_hash=c1.hash(), llm_render='world')
        # c2's hash depends on c1's hash
        self.assertNotEqual(c2.hash(), fnv1a_64('c2|0x0000000000000000|world'))


class TestPresets(unittest.TestCase):
    def test_landscape_preset(self):
        self.assertIn('sky', PRESETS['landscape']['regions'])
        self.assertIn('serene', PRESETS['landscape']['mood_choices'])
    
    def test_all_presets_have_required_keys(self):
        for name, preset in PRESETS.items():
            self.assertIn('regions', preset, f'{name} missing regions')
            self.assertIn('mood_choices', preset, f'{name} missing mood_choices')
            self.assertIn('palette_choices', preset, f'{name} missing palette_choices')
    
    def test_preset_count(self):
        self.assertEqual(len(PRESETS), 5)


class TestJevDiffusion(unittest.TestCase):
    def test_creation(self):
        d = JevDiffusion(target='a sunset over a mountain lake')
        self.assertEqual(d.target, 'a sunset over a mountain lake')
        self.assertEqual(d.preset, 'landscape')
        self.assertEqual(d.iterations, 3)
        self.assertTrue(d.use_composite_jev)
    
    def test_emit_event(self):
        d = JevDiffusion(target='test')
        event = d._emit('plan', {'regions': 'sky'})
        self.assertEqual(event.event_type, 'plan')
        self.assertEqual(len(d.events), 1)
    
    def test_to_dict(self):
        d = JevDiffusion(target='test')
        d._plan = lambda: None  # Mock
        d.plan = {'regions': 'sky', 'mood': 'serene', 'palette': 'warm', 'lighting': 1}
        d.cells = [SubstrateCell('c0', 'sky', (0, 0), llm_render='a sky')]
        d.combined = 'A sky.'
        result = d.to_dict()
        self.assertEqual(result['target'], 'test')
        self.assertEqual(result['plan']['regions'], 'sky')
        self.assertEqual(len(result['cells']), 1)
        self.assertIn('events', result)


class TestLLMBackend(unittest.TestCase):
    def test_all_backends_defined(self):
        self.assertEqual(LLMBackend.QWEN.value, 'qwen')
        self.assertEqual(LLMBackend.DEEPSEEK.value, 'deepseek')
        self.assertEqual(LLMBackend.KIMI.value, 'kimi')
        self.assertEqual(LLMBackend.JEV.value, 'jev')


if __name__ == '__main__':
    unittest.main(verbosity=2)
