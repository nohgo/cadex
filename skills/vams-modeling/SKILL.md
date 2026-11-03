---
name: vams-modeling
description: Design, implement, or verify Verilog-A, Verilog-AMS, and SV real-number models of analog or sampled mixed-signal blocks.
---

Start from the question the model must answer and the observable used to check it. Choose clocked SV/RNM for sampled values and latency. Choose Verilog-A for continuous-time electrical behavior, loading, and circuit interaction. Use Verilog-AMS when discrete events and electrical behavior interact across the boundary. Preserve the existing interface if it already supports the observable.

Specify units, polarity, differential versus single-ended conventions, reference node, sample event, and initialization. A real variable alone has no electrical loading or multi-driver resolution. In co-simulation, inspect disciplines, connect rules, supplies, thresholds, and view bindings before diagnosing a model mismatch.

Separate measured parameters, design targets, and provisional assumptions. Add bandwidth, slew, offset, jitter, or noise only when the test is sensitive to them. A comparator delay budget at one overdrive does not define a delay curve. Parameterize the assumption and compare against a transistor transient sweep when available.

Use branch contributions with explicit voltage or current orientation. Define DC behavior as well as transient startup. Use cross for threshold events with deliberate direction and initialization; a crossing may never occur at startup. Use transition for discrete target changes, a continuous transfer function for bandwidth. Keep stateful analog operators on a solver-valid execution path. Avoid timestep-dependent random draws and hard discontinuities that create convergence artifacts.

Verify with the smallest discriminating bench. For a TX FFE, check sampled tap weights and polarity with a known bit pattern, then check output swing and settling into the specified load. Compare the same stimulus, load, sample time, and units across behavioral and transistor views. Report model validity range and the largest observed discrepancy.
