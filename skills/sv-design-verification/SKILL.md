---
name: sv-design-verification
description: Write or review synthesizable SystemVerilog, digital testbenches, assertions, and clocked RNM logic for mixed-signal blocks.
---

Identify the DUT contract first. Record clock and reset behavior, port widths and signedness, handshake, sample edge, and latency in cycles where relevant. Preserve existing interfaces and filelist ordering.

For RTL, use explicit widths and signed intermediate arithmetic. Check sign extension, multiply/accumulate growth, rounding, saturation or wrap at the output. Use always_ff with nonblocking state updates and always_comb with complete assignments for combinational logic. Keep testbench timing, real arithmetic, and classes outside synthesizable logic unless the target flow explicitly supports the construct.

For verification, use the smallest self-checking bench that can falsify the change. Reuse an existing UVM agent or scoreboard when present. Add classes or constrained randomization when multiple transactions, sequences, or coverage goals justify them. Sample away from DUT update races, use an independent expected-value calculation, and bound waits with a timeout. Exercise reset, first valid output, and a relevant boundary. For an FIR, an impulse reveals tap order and latency; full-scale signed patterns reveal overflow. Check X propagation where unknowns affect the contract.

Use the project's simulator invocation, defines, top, includes, and seed. Treat a run with zero checked transactions as inconclusive. Report expected versus observed at the first failing cycle, plus the command and seed that reproduce it.
