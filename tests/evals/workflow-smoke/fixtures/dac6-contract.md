# Six-bit DAC real-number model

This is a combinational, unipolar six-bit DAC model for early mixed-signal
verification. `code` is unsigned 0..63; `vref` and `out` are wreal voltages.
When enabled, out = vref * code / 64. When disabled, out = 0 V.
The output should follow code, enable and reference changes. It models ideal
static conversion, not electrical loading, glitch energy or analog settling.
