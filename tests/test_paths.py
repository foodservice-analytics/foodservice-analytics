"""Generated artifacts can be kept outside the public source checkout."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from src.paths import PROJECT_ROOT, latest_file, output_dir


class OutputPathTests(unittest.TestCase):
    def test_external_location_overrides_config_and_is_used_by_pointers(self):
        with patch.dict(os.environ, {'FOODSERVICE_OUTPUT_DIR': '/tmp/foodservice-test-artifacts'}):
            self.assertEqual(output_dir({'output': {'dir': 'other'}}), Path('/tmp/foodservice-test-artifacts'))
            self.assertEqual(latest_file('history'), Path('/tmp/foodservice-test-artifacts/latest_presentation.txt'))

    def test_relative_default_is_anchored_to_checkout(self):
        with patch.dict(os.environ, {'FOODSERVICE_OUTPUT_DIR': ''}):
            self.assertEqual(output_dir(), PROJECT_ROOT / 'outputs')
            self.assertEqual(output_dir({'output': {'dir': 'result'}}), PROJECT_ROOT / 'result')
