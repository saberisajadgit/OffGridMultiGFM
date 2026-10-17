# How the multi-level control works

The system must supply an islanded load from several battery PCS units without a utility grid establishing frequency. A load change creates a temporary power imbalance; unequal battery charge calls for unequal power sharing, while small voltage mismatches can drive current between parallel units. The control layers address these different problems together.

## Electrical system and control paths

```text
Battery 1 ↔ GFM PCS 1 ↔ transformer / virtual impedance ─┐
Battery 2 ↔ GFM PCS 2 ↔ transformer / virtual impedance ─┼─ Islanded AC bus ↔ Load
Battery N ↔ GFM PCS N ↔ transformer / virtual impedance ─┘

Load + battery SoCs → EMS allocation → communication lag → Pref_i ─┐
Common frequency → secondary integral correction → Psec_i ────────┼→ power limit → PCS response → Pi
Common frequency → local active-power droop correction ───────────┘
Sum of Pi − load → aggregate virtual inertia / damping → common frequency
Pi → battery energy accounting → SoC_i → EMS feedback
Voltage mismatch + estimated Q → voltage compensation → voltage / circulating-current diagnostics
```

Each battery supplies its own PCS. Positive power discharges a battery; negative power charges it. The AC bus is represented by one common frequency state. The voltage path is a diagnostic approximation alongside the active-power dynamics.

## Control layers at a glance

| Layer | What it responds to | What it changes | Problem addressed | Where to look |
|---|---|---|---|---|
| PCS response and power limit | Combined active-power command | Each unit's delivered power | Finite converter response and bounded active-power output | Per-unit power |
| Primary GFM response | Generation–load imbalance and frequency deviation | Common frequency dynamics and droop power correction | Arrests frequency movement and supports rapid load sharing | Frequency and total power |
| Secondary frequency control | Persistent frequency error | Integral power correction in each PCS | Drives frequency back toward nominal when feasible | Secondary-control and frequency plots |
| Supervisory EMS | Load demand and relative battery SoC | Per-unit power allocation through a communication lag | Allocates more discharge to higher-SoC batteries | Per-unit power and SoC |
| Voltage coordination | Compensated internal-voltage differences | Per-unit voltage compensation | Reduces modeled internal-voltage mismatch and estimated circulating current | Voltage, compensation and circulating-current plots |
| Protection | PCS rating and battery SoC boundaries | Clips power commands; stops the run at a SoC boundary | Represents active-power capability and prevents continuation past a battery energy boundary | Power and termination message |

These layers operate concurrently. Their names describe their jobs; this model does not enforce a strict time-scale hierarchy between every controller.

## 1. Fast PCS response and primary grid-forming control

When the load suddenly increases, delivered power cannot change instantly. Total PCS power initially falls short of demand, and the common frequency decreases. The virtual-inertia equation determines how quickly frequency moves; damping opposes the frequency deviation.

The primary P–f droop term raises each PCS power command when frequency is below nominal and lowers it when frequency is above nominal:

`droop correction_i = −Sr × x / droop_fraction`, where `x = (f − f0) / f0`.

The commanded power passes through a first-order PCS response with time constant `power_tau_s` (default 0.05 s). A smaller `droop_fraction` produces a stronger power correction for the same frequency error. Increasing `inertia_s` reduces the initial rate of frequency change for a given imbalance; it does not add stored energy or converter capacity.

**What this solves:** the cluster responds to sudden demand before the EMS reference has fully adjusted. Droop alone can leave a frequency offset if it must supply a persistent correction. In this implementation, load feedforward from the EMS also helps remove the power imbalance.

Actual PWM, inner current/voltage loops and separate inverter phase dynamics are not simulated. Their fast active-power response is represented by the first-order power state.

## 2. Secondary frequency restoration

Each PCS integrates the common frequency error:

`dPsec_i/dt = Ki × (f0 − f)`.

Below nominal frequency, its secondary correction rises; above nominal, the correction falls. This correction is added to the delayed EMS reference and droop term. With sufficient power and energy headroom and suitable tuning, the combined controls drive frequency toward nominal.

Conditional integration blocks further secondary growth when the combined command is already saturated in the same direction. The integral can move back toward the available range when the error reverses.

**What this solves:** sustained frequency error and integral windup at the modeled active-power limit. The secondary states all receive the same frequency error and use the same gain, so this layer does not balance battery SoC by itself.

## 3. Supervisory EMS and battery SoC balancing

The EMS begins with equal sharing and adds a relative-SoC correction:

`target_i = Pload/N + Ksoc × (SoC_i − average SoC)`.

A battery above the average receives a more positive command: it discharges more, or charges less. A battery below the average discharges less, or charges more. Before saturation, the SoC corrections sum to zero, preserving the total requested load allocation. Clipping individual targets can break that equality; the frequency loop then responds to the remaining imbalance within available headroom.

For the default initial SoCs of **80%, 60%, 70%**, the average is **70%**. With `soc_gain_w_pct = 150000`, the balancing corrections are **+1.5 MW, −1.5 MW and 0 MW**. At the initial 3 MW load, the ideal EMS targets are therefore **2.5 MW, −0.5 MW and 1 MW**, before other corrections. PCS 2 can briefly charge from the islanded bus while the other units supply both it and the external load.

These targets pass through `communication_tau_s` (default 0.2 s). This is a first-order lag representing communication/processing response, not a fixed 200 ms transport delay. Initial delivered power and delayed references start at equal load sharing; they then move toward the SoC-aware targets.

**What this solves:** unequal energy use across the containers. The EMS tends to bring SoCs closer together; it does not restore their average to a fixed charge target. During positive net load, the cluster's average SoC continues to decrease. With equal battery capacities and no saturation, the ideal balancing time constant is `E/(100 Ksoc)`; with the accelerated default energy it is about 2 s, before accounting for the other dynamics.

## 4. Voltage coordination and circulating-current estimates

Small voltage-reference differences are assigned to the PCS units using a repeatable random mismatch. The model estimates branch current from active power, estimates inductive reactive consumption, and applies a Q-related voltage droop. A voltage-compensation integrator then moves each compensated internal voltage toward the mean of all units.

Transformer and virtual impedances are combined into an effective branch impedance. The circulating-current diagnostic is the largest pairwise compensated internal-voltage difference divided by `2 |Z|`, representing two equal branches between a pair of units.

**What this solves in the approximation:** voltage compensation reduces internal-voltage differences, which reduces the estimated circulating current. Compensation equalizes voltages relative to their mean; it does not restore the absolute bus voltage to nominal. Unequal branch currents can leave different estimated terminal voltages after resistive drops.

The simulation does not solve an AC network, reactive-load sharing or phase-angle-driven circulating currents. The estimated reactive power is branch inductive consumption, not an independently controlled load demand. These voltage calculations do not feed back into active-power dynamics, so their plots cannot establish actual multi-inverter voltage stability.

## 5. Power and battery protection

Each PCS command is limited to ±its active-power rating. The delivered power approaches that bounded command through the PCS response state. The model does not implement an apparent-power circle or semiconductor current limit.

Battery SoC follows the actual power and configured energy capacity. At the first lower or upper SoC boundary (default 2% / 98%), the solver stops and reports the boundary. It does not disconnect that unit and continue with the others.

**What this solves:** the study respects its modeled active-power capability and identifies when battery energy protection becomes relevant. Continued service after a trip requires load shedding, redispatch and topology-switching logic, which are outside this implementation. No controller can supply sustained demand beyond the cluster's power or available energy.

## What happens during the default load steps?

1. **At startup:** 3 MW is supplied equally, then the EMS reallocates power according to the 80/60/70% initial SoCs. Voltage compensation responds to the initial hardware mismatch.
2. **At 1 s, demand rises from 3 to 6 MW:** delivered power initially lags demand and frequency falls. Droop immediately adds power correction through the PCS response; the delayed EMS allocation and secondary integrals also adjust.
3. **As generation catches up:** the imbalance decreases and frequency returns toward 60 Hz. The unit power traces can remain unequal because SoC balancing continues.
4. **At 3 s, demand falls to 4 MW:** temporary excess generation raises frequency. Droop reduces commands, the EMS lowers its allocation, and the secondary correction adjusts.
5. **At 5.5 s, demand rises to 5.5 MW:** the same response repeats. The simulation continues to 8 s unless a battery protection boundary is reached first.

The controls divide the work: primary control responds to frequency movement, secondary control restores frequency, the EMS allocates energy use, and voltage compensation reduces estimated voltage mismatch. Their gains interact, so enabling all layers does not guarantee good tuning.

## How to investigate each layer

Use **Compare scenarios** to change one setting at a time with the same load, battery energy and initial SoCs:

- Set `secondary_w_hz_s` to zero to isolate its contribution to frequency restoration. The load-following EMS still acts, so frequency may recover even with secondary control disabled.
- Set `soc_gain_w_pct` to zero to compare equal allocation against SoC-aware sharing. Equal power from equal-capacity batteries preserves their initial SoC differences.
- Increase `communication_tau_s` to examine slower EMS response and the resulting demands on the frequency controls.
- Set `voltage_balance_gain_s` to zero to compare the estimated effect of voltage compensation. This changes voltage diagnostics, not the active-power/frequency solution.
- Increase `energy_mwh` to a realistic container capacity to study slower SoC evolution. The default is only **30 MJ = 0.00833 MWh per unit**, deliberately chosen to make balancing visible in an 8 s demonstration.

Check both frequency recovery and power/SoC headroom. Small voltage differences or a completed solver run alone are not evidence of hardware-level stability or protection compliance. See **Model & equations** for the exact implemented equations and modeling assumptions.

## From equations to Python: a guided walkthrough

The equations below are the equations actually implemented in `src/offgrid_gfm/model.py`. Each Python block is an excerpt from that file. NumPy computes the same per-unit equation for all PCS units at once: an array of length `n` holds one value per unit. A dot over a symbol means its time derivative, not a discrete change between plotted samples.

### Symbols, units and state layout

| Symbol | Meaning / units | Python name or setting |
|---|---|---|
| N | Number of equal-rated units | `n = c.units` |
| Sr | Per-unit rating, W (used as active-power limit and power base) | `rating = c.rating_mw * 1e6` |
| f0, f | Nominal and actual frequency, Hz | `c.frequency_hz`, output `frequency_hz` |
| x | Normalized frequency deviation, dimensionless | `speed` |
| Δθ | Angle deviation relative to nominal rotation, rad | `y[1]` |
| Pi | Actual PCS power, W; positive = discharge | `p[i]` |
| ri | Delayed EMS reference, W | `ref[i]` |
| zi | Secondary integral correction, W | `sec[i]` |
| ci | Voltage compensation, V | `comp[i]` |
| si | Battery SoC, percentage points (70 means 70%) | `s[i]` |
| Ei | Battery energy, J | `c.energy_mwh * 3.6e9` |

The full state vector is

$$
y=[x,\Delta\theta,P_1,\ldots,P_N,r_1,\ldots,r_N,z_1,\ldots,z_N,c_1,\ldots,c_N,s_1,\ldots,s_N]^T.
$$

```python
speed = y[0]
p, ref, sec, comp, s = y[2:].reshape(5, n)
```

For three units, the indices are `x: 0`, `angle: 1`, `p: 2–4`, `ref: 5–7`, `sec: 8–10`, `comp: 11–13`, `soc: 14–16`. Reshaping groups the last 15 entries into five rows; it does not create five independent solvers.

### A. Common frequency: power imbalance becomes frequency movement

Define the imbalance on the total cluster power base:

$$
\Delta P_{pu}=\frac{\sum_{i=1}^{N}P_i-P_L}{N S_r},\qquad
x=\frac{f-f_0}{f_0}.
$$

The normalized swing equation and angle equation are

$$
\dot x=\frac{\Delta P_{pu}-D x}{T_j},\qquad
\dot{\Delta\theta}=2\pi f_0x,\qquad f=f_0(1+x).
$$

```python
dspeed = ((p.sum()-demand(at))/(n*rating)-c.damping_pu*speed)/c.inertia_s
```

`p.sum()` is total delivered power; `demand(at)` supplies load in watts at the solver's current time. Their difference is divided by total cluster rating. `damping_pu` is dimensionless and `inertia_s` is in seconds, so `dspeed` has units 1/s. The angle derivative appears as `2*np.pi*c.frequency_hz*speed` in the returned derivative vector. The final frequency output is computed from `c.frequency_hz*(1+states[0])`.

**Numerical example:** immediately after the 3 → 6 MW step, suppose delivered power is still 3 MW and x = 0. With three 5.16 MW units and Tj = 10 s:

$$
\dot f=f_0\dot x=60\frac{(3-6)/15.48}{10}\approx-1.163\ \mathrm{Hz/s}.
$$

This is the initial slope, not a predicted sustained frequency ramp: the controls start changing power immediately afterward. The plotted frequency is the integrated outcome of that changing imbalance. The common angle is tracked but is not used in an AC network or inter-unit phase calculation.

### B. EMS allocation and communication lag

The EMS uses the mean SoC and a bounded allocation:

$$
\bar s=\frac{1}{N}\sum_i s_i,\qquad
u_i=\operatorname{clip}\left(\frac{P_L}{N}+K_s(s_i-\bar s),-S_r,S_r\right),
\qquad \dot r_i=\frac{u_i-r_i}{T_{comm}}.
$$

```python
target = np.clip(demand(at)/n + c.soc_gain_w_pct*(s-s.mean()), -rating, rating)
```

The lag derivative appears in `rhs` as:

```python
(target-ref)/c.communication_tau_s
```

`K_s = soc_gain_w_pct` has units W per percentage point; `s-s.mean()` is an array of relative SoCs. `np.clip` applies the limits independently to each unit. The target is algebraic and can jump with the load; `ref` is a state and evolves continuously.

For a constant target, the lag has the response

$$
r_i(t)=u_i+[r_i(t_0)-u_i]e^{-(t-t_0)/T_{comm}}.
$$

After one time constant the reference has moved approximately 63% toward that fixed target. With Tcomm = 0.2 s, response begins immediately rather than waiting 0.2 s. In the complete model, targets also move as SoCs evolve, so this closed-form expression describes a fixed-target example.

**Code-to-plot connection:** `ref/1e6` is exported as `pcsN_ems_mw`; it is available in the results CSV. The dashboard's power panel shows actual `p/1e6`, which also includes droop and secondary effects and therefore need not equal the EMS target or delayed reference.

### C. Secondary control and conditional anti-windup

Before anti-windup is applied,

$$
\dot z_i=K_i(f_0-f)=-K_if_0x.
$$

```python
dsec = np.full(n, -c.secondary_w_hz_s*c.frequency_hz*speed)
```

`K_i = secondary_w_hz_s` has units W/(Hz·s), so integrating `dsec` produces a power correction in watts. `np.full` gives every unit the same frequency-error derivative before checking its own saturation condition.

For example, a frequency error of −0.1 Hz with Ki = 8,000,000 W/(Hz·s) gives a secondary ramp of **+0.8 MW/s per unit**, while that error persists and the unit is not blocked by anti-windup.

Let the unlimited combined command be ai. The implemented rule is

$$
\dot z_i\leftarrow0\quad\text{if}\quad
(a_i\ge S_r\ \text{and}\ \dot z_i>0)\ \text{or}\
(a_i\le-S_r\ \text{and}\ \dot z_i<0).
$$

```python
dsec[((command_unlimited >= rating)&(dsec > 0)) |
     ((command_unlimited <= -rating)&(dsec < 0))] = 0
```

This freezes integration only when it would push the combined command farther beyond a limit. It does not reset `sec` to zero or clip the integral state itself. An error of the opposite sign can still move the integral back. `sec/1e6` produces the secondary-control plot.

### D. Primary droop, combined command and delivered power

With droop fraction R and PCS response time Tf:

$$
a_i=r_i+z_i-\frac{S_r}{R}x,\qquad
b_i=\operatorname{clip}(a_i,-S_r,S_r),\qquad
\dot P_i=\frac{b_i-P_i}{T_f}.
$$

```python
command_unlimited = ref+sec-rating/c.droop_fraction*speed
command = np.clip(command_unlimited, -rating, rating)
```

The delivered-power derivative is returned as:

```python
(command-p)/c.power_tau_s
```

The droop fraction is dimensionless: R = 0.01 means a 1% frequency deviation corresponds to one unit rating of droop correction before saturation. At 60 Hz, a −0.1 Hz deviation gives

$$
-\frac{5.16\ \mathrm{MW}}{0.01}\frac{-0.1}{60}=+0.86\ \mathrm{MW}
$$

per unit. This is added to the delayed EMS reference and the secondary correction. It is a command contribution, not instantaneous delivered power. With Tf = 0.05 s, `p` follows the bounded total command continuously. The actual power panel displays these `p` states and their sum; it does not display the unlimited command.

### E. Battery energy and the origin of SoC balancing

For lossless battery accounting,

$$
E_i=E_{i,\mathrm{MWh}}\,3.6\times10^9\ \mathrm{J},\qquad
\dot s_i=-\frac{100P_i}{E_i}.
$$

```python
ds = -p/(c.energy_mwh*3.6e9)*100
```

Watts are joules per second, making `ds` percentage points per second. The default 30 MJ battery delivering 1 MW loses **3.333 percentage points per second**. At −1 MW it gains the same amount, because charging/discharging efficiencies are not modeled.

Why does the EMS equalize SoC? For equal energy E, ideal instantaneous tracking, no saturation and no extra power corrections, define ei = si − mean(s). The equal load-sharing component cancels when subtracting the mean:

$$
\dot e_i=-\frac{100K_s}{E}e_i,\qquad
 e_i(t)=e_i(0)e^{-t/\tau_{soc}},\qquad
\tau_{soc}=\frac{E}{100K_s}.
$$

For E = 30 MJ and Ks = 150,000 W/percentage point, this ideal time constant is 2 s. Actual curves also reflect communication lag, power response, frequency correction and saturation. The SoC plot displays `s` directly; the cluster mean can decline even while differences shrink.

### F. Voltage droop, compensation and diagnostics

The three-phase rating defines the base impedance and nominal phase RMS voltage:

$$
V_\phi=\frac{V_{LL}}{\sqrt3},\quad Z_b=\frac{V_{LL}^2}{S_r},\quad
R_b=Z_b(R_{tr,pu}+R_{v,pu}),\quad
X_b=Z_b(X_{tr,pu}+X_{v,pu}).
$$

```python
vp = c.voltage_ll_v / np.sqrt(3)
zb = c.voltage_ll_v**2 / rating
r, x = zb*(c.transformer_r_pu+c.virtual_r_pu), zb*(c.transformer_x_pu+c.virtual_x_pu)
```

Here the Python name `x` is branch reactance in ohms, whereas the mathematical x above denotes normalized frequency. Inside `rhs`, normalized frequency is always named `speed`. The distinction matters when reading the code.

The diagnostic calculations use fixed nominal phase voltage for the current estimate:

$$
I_i=\frac{P_i}{3V_\phi},\quad Q_i=3I_i^2X_b,\quad
n_q=\frac{q_{droop}V_\phi}{S_r},\quad
V_{raw,i}=V_\phi m_i-n_qQ_i.
$$

```python
current = p/(3*vp)
q = 3*current**2*x
raw = vp*(mismatch[:, None] if p.ndim == 2 else mismatch) - c.q_droop_fraction*vp/rating*q
```

The seeded multiplier `mismatch` is mi. The shape check supports both a single evaluation (N values) and post-processing all output times (an N × samples array). Squaring current makes this inductive-consumption estimate nonnegative even during charging; it is not a signed reactive-load command.

Compensated internal voltage and its balancing law are

$$
U_i=V_{raw,i}+c_i,\quad \bar U=\frac1N\sum_i U_i,\qquad
\dot c_i=-K_v(U_i-\bar U).
$$

```python
_, _, raw, _ = electrical(p, comp)
dv = -c.voltage_balance_gain_s*(raw+comp-(raw+comp).mean())
```

Kv has units 1/s. A unit 1 V above the mean with Kv = 10/s receives a compensation derivative of −10 V/s. For constant raw voltages, differences decay with time constant 1/Kv; zero gain disables compensation. The derivatives sum to zero, so the controller corrects relative differences without independently restoring the mean voltage.

The displayed diagnostics are

$$
V_{term,i}=U_i-I_iR_b,\qquad
I_{circ,max}=\max_{i,j}\frac{|U_i-U_j|}{2\sqrt{R_b^2+X_b^2}},\qquad
V_{comp,norm}=\sqrt{\sum_i c_i^2}.
$$

```python
internal = raw+comp
circ = np.max(np.abs(internal[:, None, :]-internal[None, :, :]), axis=(0, 1))/(2*np.hypot(r, x))
```

`electrical()` returns terminal voltage as `raw+comp-current*r`. Post-processing exports `q/1e6`, terminal phase voltage, `circ`, and `np.linalg.norm(comp, axis=0)` to their respective panels. A growing compensation norm can accompany a shrinking circulating-current estimate: the compensation effort is increasing to cancel a mismatch. These are algebraic estimates and compensation states, not a solved network voltage or actual circulating-current measurement.

### G. SoC event equations and solver termination

The two event functions measure remaining distance to the closest battery boundary:

$$
g_{low}(y)=\min_i(s_i-s_{min}),\qquad
g_{high}(y)=\min_i(s_{max}-s_i).
$$

```python
def lower(at, state):
    return np.min(state[-n:]-c.soc_min_pct)
def upper(at, state):
    return np.min(c.soc_max_pct-state[-n:])
lower.terminal = upper.terminal = True
lower.direction = upper.direction = -1
```

`state[-n:]` selects the last N states, which are the SoCs. Both functions start positive because initial SoCs must lie strictly inside the limits. A downward zero crossing means at least one battery has reached a bound; `terminal = True` asks the integrator to stop there. This is why the plots can end before the requested load profile ends. It is not implemented by clipping SoC after a completed integration.

### H. How Python advances all these equations together

`rhs(at, y)` returns the derivatives in exactly the same order as the state vector:

```python
return np.r_[dspeed, 2*np.pi*c.frequency_hz*speed, (command-p)/c.power_tau_s,
             (target-ref)/c.communication_tau_s, dsec, dv, ds]
```

`np.r_` concatenates two scalar derivatives and five arrays of length N. The initial state is assembled in that same order:

```python
p0 = np.full(n, load[0]*1e6/n)
y = np.r_[0., 0., p0, p0, np.zeros(2*n), soc]
```

Frequency deviation and angle start at zero; actual power and delayed EMS references start at equal load sharing; secondary and voltage-compensation states start at zero. Unequal initial SoCs then cause the EMS target to differ from the initial reference.

Within each load interval the integration call is:

```python
sol = solve_ivp(interval_rhs, (t[i], end), y, method='Radau', rtol=1e-6, atol=1e-7,
                dense_output=True, events=(lower, upper))
```

Radau is an implicit adaptive integrator suitable for the combination of fast PCS response and slower control/energy states. It evaluates the whole derivative vector at trial states, adjusts internal time steps to its error tolerances, and locates protection events. The tolerances apply to each state in its native numerical units; they are not a statement of physical model accuracy.

The code splits at every input timestamp. In step mode it evaluates the old load just before an interval's right endpoint, then uses the new load on the next interval. States remain continuous across the load change; their derivatives can change abruptly. This avoids smearing a step across a single integration interval.

`dense_output=True` supplies interpolated state values for plotting between accepted solver steps. The exported plot samples are therefore different from the solver's internal time steps. The code samples approximately every 10 ms on short input intervals, capped at 200 output points per interval; long intervals can under-resolve transient extrema in the displayed curves.

Finally, the integrated states are reshaped into five N × samples arrays, converted from W to MW where appropriate, and passed to the eight-panel report. The dashboard therefore shows the solution of the coupled differential equations, plus the algebraic electrical estimates evaluated along that solution. Use **Source & downloads → model.py** to inspect the complete implementation beside this explanation.
