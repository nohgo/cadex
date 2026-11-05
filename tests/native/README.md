# Opt-in native helper regression

These jobs create/modify **eval_ic** only in a new disposable UF gpdk180 project.
They are not part of the unlicensed unit suite. Never run them in a working
Cadence project or an existing GUI. Set `CADEX_TEST_RECIPES` to the absolute
candidate `live/recipes.il` path, create a disposable Cadex full project with
profile `uf-gpdk180`, add `DEFINE eval_ic ./eval_ic` to its new `cadence/cds.lib`,
and run `seed.il`, then `recipes.il` with `cadex skill` from its cadence directory.
Require exit 0, completion markers, `NATIVE_RECIPES_PASS`, and a separate native
`cadex netlist eval_ic bias_demo` with `dc=0.7`, `dc=1.0`, MOS width 12u, and
source/bulk at simulator ground 0. The fixture intentionally has no external ports.

The regression checks native child ownership, deduplication, local ground move,
in-place wire stretch, attached-label deletion refusal, pre-mutation guards,
real source CDF mapping and PDK callback preservation. It does not establish
visual completion or general routing/topology correctness.
