# Model provenance and equations

Reconstructed from the eleven supplied photographs of Off_grid_3_PCSs.ipynb. This is an independent implementation, not an exact recovery of the notebook. Missing plot panels were reconstructed from the available states. No external grid or double-conversion rectifier is present.

The state vector has 2 + 5N entries: common normalized frequency deviation, common angle, per-unit active power, delayed EMS reference, secondary frequency integral, voltage compensation, and battery SoC. It reproduces 17 states when N = 3. All units share one frequency; individual phase synchronization and inter-inverter oscillatory modes are outside this approximation.

Let x = (f-f0)/f0, Sr be the rating of one unit, and Pload be total demand:

- Tj dx/dt = (sum(Pi)-Pload)/(N Sr) - D x; angle derivative = 2 pi f0 x.
- EMS target_i = clip(Pload/N + Ksoc(SoCi-mean(SoC)), -Sr, Sr).
- Tcomm dPref_i/dt = target_i-Pref_i. This is a first-order lag, not a pure transport delay.
- dPsec_i/dt = -Ki f0 x, with conditional integration at power saturation.
- Tf dPi/dt = clip(Pref_i+Psec_i-Sr x/droop_fraction, -Sr, Sr)-Pi.
- dSoCi/dt = -100 Pi/Ei, with Ei in joules.

Deliberate corrections to the screenshot:

1. The photographed J = Tj Sr/omega0^2 was used directly against watts in an angular-acceleration equation. This implementation uses the normalized swing equation above for consistent units. D is normalized damping, not the screenshot's derived mechanical damping. Frequency plots therefore will not exactly match the photographs.
2. Balanced three-phase impedance base is VLL^2/Sr, instead of Vphase^2/Sr. Transformer and virtual R/X remain 0.005/0.075 and 0.01/0.05 pu by default.
3. PCS active power is limited to ±rating, with secondary anti-windup. Merely clamping an EMS target at a SoC limit does not stop delayed output or secondary control from discharging a depleted battery. The solver therefore terminates at the first 2% or 98% crossing. Results include the crossing point. Post-trip load redistribution, restart, load shedding and topology switching are not implemented.
4. Pairwise circulating current uses the voltage difference divided by two branch impedances (2|Z|). This remains a magnitude-only estimate, not an AC network solution.

Voltage diagnostics retain the photographed approximations: I = P/(3 Vphase), Q = 3 I^2 X, Vraw = Vphase*mismatch - nq Q; nq = 0.02 Vphase/Sr. Compensation drives each compensated internal voltage toward their mean. Estimated terminal phase RMS voltage subtracts I R. Q here estimates branch inductive consumption; no independent reactive load, phasor load flow, voltage regulator dynamics or reactive current limits are solved. Voltage estimates do not feed back into active power. The plotted compensation norm is the Euclidean norm across units, not a physical bus voltage.

The random voltage mismatch is fixed by seed 42. Default SoCs are 80/60/70% in the UI. Per-unit energy is 30 MJ = 0.008333 MWh, matching the screenshot's intentionally accelerated SoC experiment. This is not a full-size storage container. Set real energy explicitly. Power is lossless for battery accounting; losses, DC link, BMS dynamics, unbalance, harmonics and switching are omitted.

Each input interval is solved separately with Radau so load steps cannot be skipped. Output is sampled at approximately 10 ms for short intervals, capped at 200 points per input interval. Long-interval transient extrema may be under-resolved in exports. CSV time must increase strictly and both columns must be finite. Initial load must fit the cluster rating. Later overload is represented by power saturation and frequency drift; there is no frequency trip. Session scenarios are temporary; export ZIP files to retain evidence.
