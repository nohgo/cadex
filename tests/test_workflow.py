"""Behavioral contracts for project/output isolation and honest native results."""
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workflow'))
import project
import runs
import native
import formats
import skill

PEX = '''* synthetic, no vendor data
.SUBCKT buffer VDD VSS IN OUT
M1 OUT#1 IN VSS VSS nmos L=5e-7 W=2e-6
+ AD=1e-12 AS=1e-12 fw=2e-6 simW=2e-6
R1 OUT OUT#1 2.5
C1 OUT#1 VSS 1e-14
.ENDS buffer
'''


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cadex-workflow-')
        self.root = Path(self.tmp.name).resolve() / 'chip'
        project.initialize(self.root, 'full', 'uf-gpdk180')
        self.p = project.discover(self.root / 'cadence')

    def tearDown(self):
        self.tmp.cleanup()

    def sources(self):
        paths = []
        for view, name in [('schematic', 'sch.oa'), ('layout', 'layout.oa')]:
            p = self.root / 'cadence/lib/buffer' / view / name
            p.parent.mkdir(parents=True)
            p.write_text('synthetic saved view, not an OA database\n')
            paths.append(p)
        return paths

    def fake_profile(self):
        root = Path(self.tmp.name) / 'pdk'
        for path in ['pv/assura/drc.rul', 'pv/assura/extract.rul', 'pv/assura/compare.rul', 'pv/assura/rcx/qrcTechFile']:
            p = root/path;p.parent.mkdir(parents=True, exist_ok=True);p.write_text('fixture')
        return {'pdk':str(root), 'assura':'fixture-assura', 'quantus':'fixture-qrc', 'model_mapping':{'nmos':'nmos1','pmos':'pmos1'}}

    def test_full_and_small_layout_and_ancestor_discovery(self):
        self.assertEqual(self.p['root'], self.root)
        self.assertEqual(self.p['cadence'], self.root/'cadence')
        self.assertTrue((self.root/'.agents/skills').is_dir())
        small = Path(self.tmp.name).resolve()/'tiny'
        project.initialize(small, 'small')
        p = project.discover(small)
        self.assertEqual(p['cadence'], small)
        self.assertFalse((small/'rtl').exists())
        self.assertFalse((small/'cadence').exists())

    def test_sar_shaped_adoption_preserves_existing_setup_and_source(self):
        p = Path(self.tmp.name)/'sar-shaped'
        (p/'cadence').mkdir(parents=True)
        files = {'cadence/cds.lib':'DEFINE mylib existing\n', 'cadence/.cdsinit':'user startup\n',
                 'AGENTS.md':'my existing instructions\n', '.gitignore':'existing ignore\n', 'sar-adc-rtl/design.sv':'user source\n', 'cadence/private/cell/schematic/test.cdslck':'leave lock alone\n'}
        for name,text in files.items():
            f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
        result=project.initialize(p,'full','uf-gpdk180')
        for name,text in files.items():self.assertEqual((p/name).read_text(),text)
        self.assertIn('AGENTS.md',result['preserved'])
        self.assertFalse((p/'rtl').exists())

    def test_output_escape_and_overlap_are_rejected(self):
        f=self.root/'cadex.json';data=json.loads(f.read_text())
        for value in ['../outside','cadence']:
            data['paths']['results']=value;f.write_text(json.dumps(data))
            with self.assertRaises(project.Error):project.discover(self.root)

    def test_legacy_discovery_is_read_only(self):
        p=Path(self.tmp.name)/'legacy';p.mkdir();(p/'cds.lib').write_text('preserve')
        before=list(p.iterdir());found=project.discover(p)
        self.assertTrue(found['legacy'])
        self.assertEqual(list(p.iterdir()),before)
        self.assertNotIn(p,found['results'].parents)

    def test_runs_unique_and_stale_on_source_or_project_change(self):
        source=self.root/'tb/input.scs';source.write_text('fixture')
        a=runs.Run(self.p,'simulation','buffer NN 27C',[source])
        b=runs.Run(self.p,'simulation','buffer NN 27C',[source])
        self.assertNotEqual(a.path,b.path)
        a.finish(0,{'scope':'execution only'})
        self.assertTrue((a.path/'completion.ok').exists())
        source.write_text('changed')
        self.assertIn(str(source),runs.fresh(a.data))
        self.assertEqual(runs.status(self.p)[0]['state'],'stale')
        self.assertEqual(a.data['engineering_acceptance'],'not_assessed')

    def test_changed_input_during_run_is_inconclusive_without_marker(self):
        source=self.root/'tb/input.scs';source.write_text('fixture')
        r=runs.Run(self.p,'simulation','mutation',[source]);source.write_text('different')
        r.finish(0,{})
        self.assertEqual(r.data['state'],'inconclusive')
        self.assertFalse((r.path/'completion.ok').exists())

    def test_dependency_and_status_require_valid_completion_marker(self):
        r=runs.Run(self.p,'netlist','interrupted-finish');r.finish(0,{})
        runs.load_run(r.path,'netlist')
        for invalid in [None, 'another run completed\n']:
            marker=r.path/'completion.ok'
            if invalid is None:marker.unlink()
            else:marker.write_text(invalid)
            with self.assertRaisesRegex(project.Error,'completion marker'):runs.load_run(r.path,'netlist')
            self.assertEqual(runs.status(self.p)[0]['state'],'incomplete')

    def test_batch_mapping_mutation_keeps_identities_without_masking_changed_job(self):
        job=self.root/'agent/work/build.il';job.write_text('printf("fixture")\n')
        mapping=self.p['cadence']/'cds.lib'
        original=runs.digest(mapping)
        def fake(run,*args,**kwargs):
            batch=run.path/'native/batch';batch.mkdir()
            (batch/'completion.ok').write_text('fixture completion')
            mapping.write_text(mapping.read_text()+'DEFINE fixture owned\n')
            return batch
        with patch.object(native,'skill_job',side_effect=fake):
            result=native.run_skill(self.p,job,'add-library')
        self.assertEqual(result['state'],'complete')
        _, data=runs.load_run(result['run'])
        before=next(i for i in data['inputs'] if i['path']==str(mapping))
        after=next(i for i in data['post_inputs'] if i['path']==str(mapping))
        self.assertEqual(before['sha256'],original)
        self.assertNotEqual(before['sha256'],after['sha256'])
        def changed_job(run,*args,**kwargs):
            batch=fake(run)
            job.write_text('different job')
            return batch
        with patch.object(native,'skill_job',side_effect=changed_job):
            result=native.run_skill(self.p,job,'unexpected-job-mutation')
        self.assertEqual(result['state'],'inconclusive')

    def test_artifact_tamper_and_project_serialization(self):
        r=runs.Run(self.p,'lvs','fixture');f=r.path/'native/match.csm';f.write_text('match')
        r.artifact('report',f);r.finish(0,{})
        f.write_text('tampered')
        with self.assertRaisesRegex(project.Error,'artifact'):runs.load_run(r.path)
        with runs.serialized(self.p):
            with self.assertRaisesRegex(project.Error,'active'):
                with runs.serialized(self.p):pass

    def test_site_setup_isolated_and_strict_flags_neutralized(self):
        settings=Path(self.tmp.name)/'settings'
        settings.write_text('set -e\nset +e\nfalse\nprintf "%s" "$UNSET_CADEX_FIXTURE" >/dev/null\nprintf overwritten > cds.lib\nprintf startup > .cdsinit\ntrue\n')
        original=(self.p['cadence']/'cds.lib').read_bytes()
        r=runs.Run(self.p,'simulation','env')
        with patch.object(native,'SETUP',native.SETUP.replace('/apps/settings',shlex.quote(str(settings)))):
            code=native.execute(r,self.p,['bash','-c','printf success; test -n "$TMPDIR"'])
        self.assertEqual(code,0)
        self.assertEqual((self.p['cadence']/'cds.lib').read_bytes(),original)
        self.assertFalse((self.p['cadence']/'.cdsinit').exists())
        self.assertEqual((r.path/'setup/cds.lib').read_text(),'overwritten')

    def test_setup_failure_does_not_execute_program(self):
        settings=Path(self.tmp.name)/'bad-settings';settings.write_text('return 7\n')
        r=runs.Run(self.p,'simulation','bad-env');sentinel=self.root/'unwanted'
        with patch.object(native,'SETUP',native.SETUP.replace('/apps/settings',shlex.quote(str(settings)))):
            code=native.execute(r,self.p,['touch',str(sentinel)])
        self.assertEqual(code,7);self.assertFalse(sentinel.exists())

    def test_timeout_terminates_only_owned_job_group(self):
        settings=Path(self.tmp.name)/'settings';settings.write_text('true\n')
        r=runs.Run(self.p,'simulation','timeout');sentinel=self.root/'unwanted-child'
        child='import time,pathlib; time.sleep(.5); pathlib.Path({!r}).write_text("orphan")'.format(str(sentinel))
        program='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{!r}]); time.sleep(5)'.format(child)
        with patch.object(native,'SETUP',native.SETUP.replace('/apps/settings',shlex.quote(str(settings)))):
            code=native.execute(r,self.p,[sys.executable,'-c',program],timeout=.15)
        self.assertEqual(code,124)
        time.sleep(.6)
        self.assertFalse(sentinel.exists())

    def test_pex_uses_owned_lvs_copy_and_preserves_original_evidence(self):
        sch,lay=self.sources();pr=self.fake_profile()
        lvs=runs.Run(self.p,'lvs','matched',[sch,lay])
        lvs.data.update(profile=pr,target={'library':'lib','cell':'buffer','view':'layout'})
        report=lvs.path/'native/buffer.csm';report.write_text('Schematic and Layout Match\n')
        data=lvs.path/'native/buffer.ldb';data.write_text('unchanged-native-data')
        lvs.artifact('report',report);lvs.artifact('native/buffer.ldb',data);lvs.finish(0,{'matched':True})
        before={p.name:p.read_bytes() for p in (lvs.path/'native').iterdir()}
        def fake(run,*args,**kwargs):
            self.assertEqual((run.path/'native/lvs/buffer.ldb').read_text(),'unchanged-native-data')
            command=(run.path/'inputs/qrc.cmd').read_text()
            self.assertIn('-temporary_directory_name qrc_tmp',command)
            self.assertNotIn(str(lvs.path/'native')+' ',command)
            (run.path/'stdout.log').write_text('fixture')
            (run.path/'native/qrc.log').write_text('Total floating nets = 0\nQuantus terminated normally\n')
            (run.path/'native/lvs/buffer_pex.sp').write_text(PEX)
            return 0
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute',side_effect=fake):
            result=native.pex(self.p,lvs.path,'extracted','VSS')
        self.assertEqual(result['state'],'complete')
        self.assertEqual(result['evidence']['M'],1)
        self.assertEqual({p.name:p.read_bytes() for p in (lvs.path/'native').iterdir()},before)
        sch.write_text('changed schematic')
        with patch.object(native,'execute') as execute:
            with self.assertRaisesRegex(project.Error,'source changed'):native.pex(self.p,lvs.path,'stale','VSS')
            execute.assert_not_called()

    def test_native_drc_zero_exit_with_violations_is_not_complete(self):
        self.sources();pr=self.fake_profile()
        def fake(run,*args,**kw):
            (run.path/'stdout.log').write_text('Total errors: 1 1\nAssura terminated normally\n');return 0
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute',side_effect=fake):
            result=native.physical(self.p,'lib','buffer','bad-drc','drc')
        self.assertEqual(result['state'],'failed')
        self.assertEqual(result['native_exit'],0)
        self.assertFalse((Path(result['run'])/'completion.ok').exists())

    def test_native_drc_actual_zero_totals_records_completion(self):
        self.sources();pr=self.fake_profile()
        def fake(run,*args,**kw):
            (run.path/'stdout.log').write_text('Total errors: 0 0\nAssura terminated normally\n');return 0
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute',side_effect=fake):
            result=native.physical(self.p,'lib','buffer','clean-drc','drc')
        self.assertEqual(result['state'],'complete')
        self.assertTrue((Path(result['run'])/'completion.ok').exists())

    def test_nested_native_database_is_fingerprinted_and_tamper_rejected(self):
        self.sources();pr=self.fake_profile()
        def fake(run,*args,**kw):
            (run.path/'stdout.log').write_text('Total errors: 0 0\nAssura terminated normally\n')
            database=run.path/'native/buffer.lvsdb/status'
            database.parent.mkdir();database.write_text('native fixture')
            return 0
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute',side_effect=fake):
            result=native.physical(self.p,'lib','buffer','nested-db','drc')
        path, data=runs.load_run(result['run'])
        self.assertIn('native/buffer.lvsdb/status',data['artifacts'])
        (path/'native/buffer.lvsdb/status').write_text('changed')
        with self.assertRaisesRegex(project.Error,'artifact changed'):runs.load_run(path)

    def test_lvs_dependency_target_and_pin_error_gate(self):
        sch,lay=self.sources();pr=self.fake_profile()
        r=runs.Run(self.p,'netlist','fixture',[sch]);f=r.path/'native/input.scs'
        f.write_text('simulator lang=spectre\nM1 (OUT IN VSS VSS) nmos1 w=(2u) l=500n m=(1)*(1)\nsimulatorOptions options temp=27\n')
        r.artifact('netlist',f);r.data.update(target={'library':'lib','cell':'buffer','view':'schematic'},ports=['IN','OUT','VSS']);r.finish(0,{})
        def fake(run,*args,**kw):
            (run.path/'stdout.log').write_text('Assura terminated normally\n')
            (run.path/'native/buffer.csm').write_text('buffer | matched, pin errs\nMismatch between Schematic and Layout\n')
            return 0
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute',side_effect=fake):
            result=native.physical(self.p,'lib','buffer','pin-error','lvs',r.path)
        self.assertEqual(result['state'],'failed')
        sch.write_text('new schematic')
        with patch.object(native,'profile',return_value=pr),patch.object(native,'execute') as execute:
            with self.assertRaisesRegex(project.Error,'source changed'):native.physical(self.p,'lib','buffer','stale','lvs',r.path)
            execute.assert_not_called()

    def test_skill_preflight_catches_balance_and_lifecycle_without_native_run(self):
        for source in ['foreach(x list(1)) )','let((x)','exit(0)','(quit)']:
            with self.assertRaises(project.Error):skill.check(source)
        skill.check('; exit(0)\ncadexReport("parentheses ()) in a string")\n')
        skill.check('/* exit(0) ((( */ cadexReport("/* literal */")')
        with self.assertRaises(project.Error):skill.check('/* unclosed')

    def test_pex_component_translation_and_unknown_or_colliding_nodes_refuse(self):
        text,proof=formats.pex_to_spectre(PEX,{'nmos':'nmos1'})
        self.assertEqual(proof['counts'],{'M':1,'R':1,'C':1})
        self.assertEqual(proof['ports'],['VDD','VSS','IN','OUT'])
        self.assertIn('M1 (OUT_p1 IN VSS VSS) nmos1',text)
        self.assertIn('R1 (OUT OUT_p1) resistor r=2.5',text)
        for bad in [PEX.replace('R1 OUT OUT#1','R1 OUT_p1 OUT#1'),PEX.replace('nmos L','unsupported L'),PEX.replace('W=2e-6','W=3e-6')]:
            with self.assertRaises(project.Error):formats.pex_to_spectre(bad,{'nmos':'nmos1'})

    def test_cdl_adapter_rejects_unknown_devices_and_preserves_multiplicity(self):
        text='M1 (OUT IN VSS VSS) nmos1 w=(2u) l=500n m=(2)*(3)\nsimulatorOptions options temp=27\n'
        cdl,count=formats.schematic_cdl(text,'buffer',['IN','OUT','VSS'],{'nmos1':'nmos'})
        self.assertEqual(count,1);self.assertIn('m=6',cdl)
        wrapped=text.replace(' m=(2)*(3)', ' '+chr(92)+'\n        m=(2)*(3)')
        self.assertEqual(formats.schematic_cdl(wrapped,'buffer',['IN','OUT','VSS'],{'nmos1':'nmos'})[0],cdl)
        with self.assertRaises(project.Error):formats.schematic_cdl('X1 (A B) unknown\n','buffer',['A','B'],{})

    def test_psf_units_complex_samples_and_absent_data(self):
        f=self.root/'op.dc';f.write_text('HEADER\nVALUE\n"vout" "V" 0.45\n"gm" "S" 0.001 PROP(\nEND\n')
        self.assertEqual(formats.read_psf(f)[0]['gm'],.001)
        f.write_text('HEADER\nVALUE\n"freq" 1\n"out" (0.8 -0.1)\n"freq" 10\n"out" (0.7 -0.2)\nEND\n')
        self.assertEqual(len(formats.read_psf(f,'freq')),2)
        self.assertEqual(formats.read_psf(f,'freq')[0]['out'],complex(.8,-.1))
        f.write_text('not supported binary or empty output')
        with self.assertRaises(project.Error):formats.read_psf(f)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installer')
    def test_incomplete_workflow_bundle_preserves_existing_installation(self):
        home=Path(self.tmp.name)/'home'
        first=subprocess.run([sys.executable,str(ROOT/'install.py'),'--home',str(home)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        self.assertEqual(first.returncode,0,first.stderr)
        before={str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()}
        bundle=Path(self.tmp.name)/'incomplete-bundle'
        shutil.copytree(str(ROOT),str(bundle),ignore=shutil.ignore_patterns('.git','__pycache__'))
        (bundle/'workflow/runs.py').unlink()
        failed=subprocess.run([sys.executable,str(bundle/'install.py'),'--home',str(home)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        self.assertNotEqual(failed.returncode,0)
        self.assertIn('Incomplete workflow bundle',failed.stderr)
        after={str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux installer')
    def test_installed_workflow_entrypoint_works_without_skillbridge_or_activation(self):
        home=Path(self.tmp.name)/'home'
        installed=subprocess.run([sys.executable,str(ROOT/'install.py'),'--home',str(home)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        self.assertEqual(installed.returncode,0,installed.stderr)
        helper=home/'.codex/scripts/cadex'
        result=subprocess.run([str(helper),'--project',str(self.root/'cadence'),'project','show'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['cadence'],str(self.root/'cadence'))
        self.assertFalse((home/'.cdsinit').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
