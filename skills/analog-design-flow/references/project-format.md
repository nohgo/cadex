# Project layout and evidence

Use the project's existing organization. The reference on UF is
`~/asar_adc_8bit`: a root containing `cadence/`, separate RTL, stimulus, synthesis
and pictures. Referencing that structure is not permission to migrate or inspect
its design databases. Cadex initializes new projects or explicitly adopts paths;
it never moves an existing library, clears locks or replaces startup files.

## Full projects

```text
project/
  cadex.json                 Paths, explicit technology profile, optional library mappings
  AGENTS.md                  Short project entrypoint; retain existing instructions
  .agents/skills/            Only project-specific reusable skills (native discovery)
  cadence/                   Launch Virtuoso here: cds.lib, user libraries, normal Cadence files
  rtl/                       Optional digital source; existing names/subrepos may be retained
  tb/                        Intentional testbench source and stimulus
  results/<stage>/<label>/<unique-run>/
                             Native outputs, input identities, logs, manifest, completion marker
  agent/
    designs/<design>/        Requirements, assumptions, decisions and evidence index
    notes/                   Verified project procedures and durable findings
    work/                    Temporary jobs, caches and probes; ignored by Git
```

Initialize explicitly:

```bash
~/.codex/scripts/cadex project init /path/to/new-project --mode full --profile uf-gpdk180
```

Existing AGENTS.md, cds.lib, .cdsinit, .gitignore and source are preserved. No
GUI is started, environment sourced, license acquired, Git repo initialized or
permission saved by initialization. Use the user's normal GUI startup from the
configured Cadence directory, with their site environment already established.
Do not source the site's copying setup directly over project files: managed
licensed commands isolate it in their own setup directory.

`cadex.json` is the single path definition, discovered from the current directory
upward. Run `~/.codex/scripts/cadex project show` before choosing directories.
Full projects default to `cadence/`; small configured projects use `.`. Tool
invocations use the configured launch directory as tool workdir. Start Codex at
the project root, or within a Git repo so its root project skills are discoverable.
Keep native `.agents/skills` for skills, rather than hiding skills in scratch.

Optional `libraries` maps library names to project-relative paths when they are
not `<cadence>/<library>`. `ground_net` declares an extraction reference only
when known. The `uf-gpdk180` profile is an explicitly selected site recipe, not
a universal technology default. Current source adapters support the flat MOS
case demonstrated on UF; unknown devices/hierarchies require a verified native
project flow, not guessed model translations.

## Small experiments and existing launch directories

Do not scaffold a large project for a quick probe. An existing directory with
cds.lib works without cadex.json: discovery is read-only, and managed outputs go
under `~/.local/state/cadex/projects/<project-id>/`. Select a technology profile
for one invocation with `cadex --profile uf-gpdk180 ...`, without changing config.

For a durable small experiment, `project init PATH --mode small` keeps Cadence
at its root and omits RTL/testbench scaffolding. Put disposable experiment roots
under `~/.local/state/cadex/experiments/`. Do not reorganize `~/cadence_work` or
the user's active project just to conform to the template.

## Runs and provenance

Give every run a design/purpose label and record actual corner, temperature,
supply, stimulus, seed and load when applicable. Conditions on the CLI are
declared metadata, not independently proven operating conditions. Manifests
record native argv/cwd, source/config hashes, native status, evidence paths and
completion. Include DUT/model dependencies with `spectre --source` so freshness
checks cover them; include lists are not inferred transitively from arbitrary decks.

`cadex status` distinguishes failed, incomplete and stale inputs. Dependencies
are checked before LVS/PEX; explicit batch construction jobs retain before/after
library-mapping identities; extraction uses its own working copy of matched LVS
data. Keep failed attempts and old results. No automatic replay, silent overwrite
of a previous run, or movement of an unexpected output from another directory.

Tool completion and engineering acceptance are separate. A simulator returning
0, clean DRC/LVS or a rendered plot does not prove the requested gain, headroom,
settling, stability or readability. Link measurements to requirements and mark
affected results stale after design/model/bench changes. Do not change a user
requirement to rescue a failed check; changes to provisional assumptions must
retain the original failure and identify the new characterized range.

Keep global reusable mechanics in Cadex Git. Track project sources, instructions,
intent and selected reports according to project policy. Raw results, Cadence
caches/locks, generated agent work, private registrations and vendor/PDK data
are not Cadex source. Initialization supplies create-only ignore guidance; it
does not edit an existing ignore policy or delete ignored files.
