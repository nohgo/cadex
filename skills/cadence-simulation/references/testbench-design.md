# Analog testbench design

Treat the bench as a measurement system with its own assumptions and failure
modes. Separate the DUT's intended interfaces from external supplies, bias,
stimulus and load. Preserve the DUT schematic as the source of connectivity;
do not insert measurement circuitry into it merely to simplify a test.

## Establish the bench contract

Resolve actual port order and reference nodes, supply/bulk connections, model
corner and temperature, parameter values and units, source impedance, bias,
load and the input/output range. Bind every required variable; a new symbolic
bias is not a tested numerical operating condition. Confirm any intended open
output receives the appropriate load or termination in this bench. Avoid
accidentally shorting outputs with ideal sources or letting the bench provide
an unintended bias path. Bench details may be chosen from project context;
ask when a materially different load or interpretation changes the result.

Reuse existing ADE tests/configs when suitable. A text bench around a freshly
netlisted DUT is often appropriate for reproducible regressions. A schematic
bench is appropriate for requested GUI delivery or view/config integration.
Keep DUT and bench decisions explicit in either representation. Handle CDF and
model parameter conventions through the project's normal netlisting flow.

## Make the test discriminating

Check the DC solution, branch-current signs, plausible supply power, output
level and device headroom using the project's model conventions. Resolve setup
or bias failures before treating a gain curve as valid. Then select the analysis
for the question: AC around a valid operating point, transient for large-signal
behavior/startup/settling, noise for a defined bandwidth and reference, or DC
sweeps for operating range. Use appropriate loop-injection methods for stability;
do not break the DC operating point merely to measure loop gain.

Define the measured expression, units, polarity/reference, stimulus amplitude,
time/frequency window, settling exclusion, threshold and tolerance. Check that
saved signals, duration/resolution and events actually support the measurement.
Check plausible scale/sign and failure behavior so a disconnected or flat output
cannot pass through an empty measurement or permissive condition. Keep a load,
corner and sweep member attached to every result; avoid extrapolating nominal
success to all conditions. When no numerical target exists, characterize and
report the observation rather than inventing a pass threshold.

## Handoff and evidence

Provide the resolved bench, current DUT netlist identity, analyses, bound
variables, models, measurements and reproduction command/run path. Preserve
prior runs. Classify missing data, incomplete analyses and unbound variables as
inconclusive, and distinguish bench/setup failures from circuit failures. For
plots, verify the actual traces, axes, units and selected corner/sweep; rendering
a file is not evidence that the intended waveform was produced.
