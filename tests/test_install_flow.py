"""Flow packaging and safe upgrade tests; no GUI, process discovery or licenses."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {'analog-design-flow', 'analog-design', 'cadence-simulation',
          'cadence-layout', 'cadence-virtuoso', 'sv-design-verification', 'vams-modeling'}


class FlowInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cadex-flow-install-')
        self.home = Path(self.temp.name) / 'home'
        self.home.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def install(self, source=ROOT):
        return subprocess.run([sys.executable, str(source / 'install.py'), '--home', str(self.home)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def test_all_skills_and_resources_install_idempotently_without_activation(self):
        sessions = self.home / '.local/state/cadex/live/sessions'
        sessions.mkdir(mode=0o700, parents=True)
        sessions.parent.chmod(0o700)
        consent = sessions / 'existing-user-consent.json'
        consent.write_text('preserve existing registration without reading it\n')
        consent.chmod(0o600)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        deployed = self.home / '.agents/skills'
        self.assertEqual({p.parent.name for p in deployed.glob('*/SKILL.md')}, SKILLS)
        for source in (ROOT / 'skills').rglob('*'):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (deployed / source.relative_to(ROOT / 'skills')).read_bytes())
        self.assertEqual(consent.read_text(), 'preserve existing registration without reading it\n')
        self.assertFalse((self.home / '.cdsinit').exists())
        self.assertFalse((self.home / '.codex/config.toml').exists())
        again = self.install()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertNotIn('Installed:', again.stdout)

    def test_known_global_section_upgrades_preserving_surrounding_instructions(self):
        target = self.home / '.codex/AGENTS.md'
        target.parent.mkdir()
        prefix = '# My instructions\n\nKeep this exact text.\n\n'
        suffix = '\n\n## Other workflow\n\nPreserve me too.\n'
        legacy = (ROOT / 'tests/fixtures/agents-v1.md').read_text().strip()
        before = prefix + legacy + suffix
        target.write_text(before)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), prefix + (ROOT / 'AGENTS.md').read_text().strip() + suffix)
        backups = list((self.home / '.codex/ece-install-backups').rglob('AGENTS.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), before)
        self.assertEqual(self.install().returncode, 0)

    def test_unknown_global_edits_refuse_before_deploying(self):
        target = self.home / '.codex/AGENTS.md'
        target.parent.mkdir()
        for before in [(ROOT / 'tests/fixtures/agents-v1.md').read_text() + '\nUser addition inside this section.\n',
                       (ROOT / 'AGENTS.md').read_text().splitlines()[0]]:
            target.write_text(before)
            result = self.install()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('AGENTS.md', result.stderr)
            self.assertEqual(target.read_text(), before)
            self.assertFalse((self.home / '.agents').exists())

    def test_incomplete_skill_bundle_refuses_before_deploying(self):
        source = Path(self.temp.name) / 'incomplete-source'
        source.mkdir()
        for name in ['install.py', 'AGENTS.md']:
            shutil.copyfile(ROOT / name, source / name)
        for name in SKILLS - {'cadence-layout'}:
            target = source / 'skills' / name
            target.mkdir(parents=True)
            shutil.copyfile(ROOT / 'skills' / name / 'SKILL.md', target / 'SKILL.md')
        result = self.install(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cadence-layout', result.stderr)
        self.assertFalse((self.home / '.codex').exists())

    def test_shipped_skill_resource_links_resolve_inside_bundle(self):
        skills_root = (ROOT / 'skills').resolve()
        for page in skills_root.rglob('*.md'):
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', page.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                path = (page.parent / link.split('#')[0]).resolve()
                self.assertIn(skills_root, path.parents, '{}: {}'.format(page, link))
                self.assertTrue(path.is_file(), '{}: {}'.format(page, link))


if __name__ == '__main__':
    unittest.main(verbosity=2)
