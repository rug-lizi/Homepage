import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ManagementTests(unittest.TestCase):
    def test_add_edit_remove_keeps_both_outputs_in_sync(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            for name in ('data', 'scripts', 'dist'):
                shutil.copytree(ROOT / name, project / name)
            shutil.copy(ROOT / 'README.md', project / 'README.md')

            def run(*args):
                return subprocess.run([sys.executable, str(project / 'scripts/manage.py'), *args], capture_output=True, text=True)

            result = run('add-site', 'test', '--name', 'Test website', '--url', 'https://test.example.com', '--summary', 'A test project.', '--launch-date', '2026-11-13', '--launch-source', 'Test deployment', '--repository', 'Homepage')
            self.assertEqual(result.returncode, 0, result.stderr)
            for filename in ('README.md', 'dist/index.html'):
                self.assertIn('https://test.example.com', (project / filename).read_text())
            previous = (project / 'data/websites.json').read_text()
            result = run('edit-site', 'test', '--url', 'javascript:alert(1)')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((project / 'data/websites.json').read_text(), previous)
            result = run('edit-site', 'test', '--summary', 'Revised description.')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Revised description.', (project / 'dist/index.html').read_text())
            self.assertEqual(run('remove-site', 'test').returncode, 0)
            self.assertNotIn('https://test.example.com', (project / 'README.md').read_text())
            sites = json.loads((project / 'data/websites.json').read_text())['websites']
            self.assertFalse(any(s['id'] == 'test' for s in sites))


if __name__ == '__main__':
    unittest.main()
