# Model equations and assumptions

This reduced-order model represents parallel battery PCSs supplying an islanded load. No external grid or double-conversion rectifier is present.

The state vector has 2 + 5N entries: common normalized frequency deviation, common angle, per-unit active power, delayed EMS reference, secondary frequency integral, voltage compensation, and battery SoC. It reproduces 17 states when N = 3. All units share one frequency; individual phase synchronization and inter-inverter oscillatory modes are outside this approximation.

Let x = (f-f0)/f0, Sr be the rating of one unit, and Pload be total demand:

- Tj dx/dt = (sum(Pi)-Pload)/(N Sr) - D x; angle derivative = 2 pi f0 x.
- EMS target_i = clip(Pload/N + Ksoc(SoCi-mean(SoC)), -Sr, Sr).
- Tcomm dPref_i/dt = target_i-Pref_i. This is a first-order lag, not a pure transport delay.
- dPsec_i/dt = -Ki f0 x, with conditional integration at power saturation.
- Tf dPi/dt = clip(Pref_i+Psec_i-Sr x/droop_fraction, -Sr, Sr)-Pi.
- dSoCi/dt = -100 Pi/Ei, with Ei in joules.

Implementation conventions:

1. The normalized swing equation above uses consistent power and frequency units. D is normalized damping, and Tj is the virtual inertia time constant.
2. The balanced three-phase impedance base is VLL^2/Sr. Transformer and virtual R/X are 0.005/0.075 and 0.01/0.05 pu by default.
3. PCS active power is limited to +/-rating, with secondary anti-windup. Merely clamping an EMS target at a SoC limit does not stop delayed output or secondary control from discharging a depleted battery. The solver therefore terminates at the first 2% or 98% crossing. Results include the crossing point. Post-trip load redistribution, restart, load shedding and topology switching are not implemented.
4. Pairwise circulating current uses the voltage difference divided by two branch impedances (2|Z|). This is a magnitude-only estimate, not an AC network solution.

Voltage diagnostics use these approximations: I = P/(3 Vphase), Q = 3 I^2 X, Vraw = Vphase*mismatch - nq Q; nq = 0.02 Vphase/Sr. Compensation drives each compensated internal voltage toward their mean. Estimated terminal phase RMS voltage subtracts I R. Q here estimates branch inductive consumption; no independent reactive load, phasor load flow, voltage regulator dynamics or reactive current limits are solved. Voltage estimates do not feed back into active power. The plotted compensation norm is the Euclidean norm across units, not a physical bus voltage.

The random voltage mismatch is fixed by seed 42. Default SoCs are 80/60/70% in the UI. Per-unit energy is 30 MJ = 0.008333 MWh, chosen to accelerate SoC dynamics for the demonstration. This is not a full-size storage container. Set real energy explicitly. Power is lossless for battery accounting; losses, DC link, BMS dynamics, unbalance, harmonics and switching are omitted.

Each input interval is solved separately with Radau so load steps cannot be skipped. Output is sampled at approximately 10 ms for short intervals, capped at 200 points per input interval. Long-interval transient extrema may be under-resolved in exports. CSV time must increase strictly and both columns must be finite. Initial load must fit the cluster rating. Later overload is represented by power saturation and frequency drift; there is no frequency trip. Session scenarios are temporary; export ZIP files to retain evidence.
