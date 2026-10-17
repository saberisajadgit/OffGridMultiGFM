"""Coherent-frequency cluster with per-unit PCS, EMS and battery states."""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.integrate import solve_ivp

@dataclass(frozen=True)
class Config:
    units: int = 3
    rating_mw: float = 5.16
    voltage_ll_v: float = 690.0
    frequency_hz: float = 60.0
    inertia_s: float = 10.0
    damping_pu: float = 1.0
    droop_fraction: float = 0.01
    power_tau_s: float = 0.05
    communication_tau_s: float = 0.2
    secondary_w_hz_s: float = 8000000.0
    soc_gain_w_pct: float = 150000.0
    energy_mwh: float = 30e6 / 3.6e9
    mismatch_pct: float = 1.0
    transformer_r_pu: float = 0.005
    transformer_x_pu: float = 0.075
    virtual_r_pu: float = 0.01
    virtual_x_pu: float = 0.05
    q_droop_fraction: float = 0.02
    voltage_balance_gain_s: float = 10.0
    soc_min_pct: float = 2.0
    soc_max_pct: float = 98.0
    seed: int = 42

    def __post_init__(self):
        if isinstance(self.units, bool) or not isinstance(self.units, int) or not 2 <= self.units <= 12:
            raise ValueError("PCS count must be an integer from 2 to 12")
        for k, v in asdict(self).items():
            if not np.isfinite(v):
                raise ValueError(f"{k} must be finite")
        for k in ('rating_mw', 'voltage_ll_v', 'frequency_hz', 'inertia_s', 'droop_fraction', 'power_tau_s', 'communication_tau_s', 'energy_mwh'):
            if getattr(self, k) <= 0:
                raise ValueError(f"{k} must be positive")
        for k in ('damping_pu', 'secondary_w_hz_s', 'soc_gain_w_pct', 'mismatch_pct', 'transformer_r_pu', 'transformer_x_pu', 'virtual_r_pu', 'virtual_x_pu', 'q_droop_fraction', 'voltage_balance_gain_s'):
            if getattr(self, k) < 0:
                raise ValueError(f"{k} cannot be negative")
        if self.mismatch_pct >= 100 or not 0 <= self.soc_min_pct < self.soc_max_pct <= 100 or self.seed < 0 or int(self.seed) != self.seed:
            raise ValueError("Invalid mismatch, SoC bounds, or random seed")
        if self.transformer_r_pu + self.virtual_r_pu + self.transformer_x_pu + self.virtual_x_pu == 0:
            raise ValueError("Impedance must be nonzero")


def simulate(time_s, load_mw, config=None, initial_soc=None, interpolation='step'):
    c = config or Config()
    t, load = np.asarray(time_s, dtype=float), np.asarray(load_mw, dtype=float)
    if t.ndim != 1 or t.shape != load.shape or len(t) < 2 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(load)) or np.any(np.diff(t) <= 0):
        raise ValueError("Supply matching finite time/load vectors with strictly increasing time")
    if len(t) > 100000 or t[-1] - t[0] > 86400:
        raise ValueError("Interactive limit: 100000 input samples and 24 hours")
    if interpolation not in ('step', 'linear'):
        raise ValueError("Interpolation must be step or linear")
    n, rating = c.units, c.rating_mw * 1e6
    soc = np.asarray(initial_soc if initial_soc is not None else np.linspace(80, 60, n), dtype=float)
    if soc.shape != (n,) or not np.all(np.isfinite(soc)) or np.any(soc <= c.soc_min_pct) or np.any(soc >= c.soc_max_pct):
        raise ValueError("Initial SoCs must lie strictly inside the configured protection bounds")
    if abs(load[0]) > n*c.rating_mw:
        raise ValueError("Initial load exceeds cluster rating; cannot initialize an equilibrium")
    vp = c.voltage_ll_v / np.sqrt(3)
    # Balanced three-phase base: total three-phase rating / phase impedance.
    zb = c.voltage_ll_v**2 / rating
    r, x = zb*(c.transformer_r_pu+c.virtual_r_pu), zb*(c.transformer_x_pu+c.virtual_x_pu)
    mismatch = np.random.RandomState(c.seed).uniform(1-c.mismatch_pct/100, 1+c.mismatch_pct/100, n)
    def demand(at):
        if interpolation == 'linear':
            return np.interp(at, t, load)*1e6
        return load[np.clip(np.searchsorted(t, at, side='right')-1, 0, len(t)-1)]*1e6
    def electrical(p, comp):
        current = p/(3*vp)
        q = 3*current**2*x
        raw = vp*(mismatch[:, None] if p.ndim == 2 else mismatch) - c.q_droop_fraction*vp/rating*q
        return current, q, raw, raw+comp-current*r
    # df/f0, angle, P, delayed EMS, secondary, voltage compensation, SoC
    def rhs(at, y):
        speed = y[0]
        p, ref, sec, comp, s = y[2:].reshape(5, n)
        target = np.clip(demand(at)/n + c.soc_gain_w_pct*(s-s.mean()), -rating, rating)
        command_unlimited = ref+sec-rating/c.droop_fraction*speed
        command = np.clip(command_unlimited, -rating, rating)
        dsec = np.full(n, -c.secondary_w_hz_s*c.frequency_hz*speed)
        # Conditional integration prevents secondary windup at PCS power limits.
        dsec[((command_unlimited >= rating)&(dsec > 0)) | ((command_unlimited <= -rating)&(dsec < 0))] = 0
        _, _, raw, _ = electrical(p, comp)
        dv = -c.voltage_balance_gain_s*(raw+comp-(raw+comp).mean())
        ds = -p/(c.energy_mwh*3.6e9)*100
        # Tj*d(Delta omega/omega0)/dt = power imbalance / cluster rating - D*speed.
        dspeed = ((p.sum()-demand(at))/(n*rating)-c.damping_pu*speed)/c.inertia_s
        return np.r_[dspeed, 2*np.pi*c.frequency_hz*speed, (command-p)/c.power_tau_s,
                     (target-ref)/c.communication_tau_s, dsec, dv, ds]
    p0 = np.full(n, load[0]*1e6/n)
    y = np.r_[0., 0., p0, p0, np.zeros(2*n), soc]
    def lower(at, state):
        return np.min(state[-n:]-c.soc_min_pct)
    def upper(at, state):
        return np.min(c.soc_max_pct-state[-n:])
    lower.terminal = upper.terminal = True
    lower.direction = upper.direction = -1
    # Split every load interval so the solver cannot skip step changes.
    ts, ys, termination = [t[0]], [y.copy()], 'Completed'
    for i in range(len(t)-1):
        end = t[i+1]
        def interval_rhs(at, state):
            return rhs(min(at, np.nextafter(end, t[i])), state) if interpolation == 'step' else rhs(at, state)
        sol = solve_ivp(interval_rhs, (t[i], end), y, method='Radau', rtol=1e-6, atol=1e-7,
                        dense_output=True, events=(lower, upper))
        if not sol.success:
            raise RuntimeError(sol.message)
        sample = np.linspace(t[i], sol.t[-1], max(2, min(201, int((end-t[i])/0.01)+1)))[1:]
        ts.extend(sample)
        ys.extend(sol.sol(sample).T)
        y = sol.y[:, -1]
        if sol.status == 1:
            termination = 'Stopped at battery SoC protection boundary; restart/topology change is not modeled'
            break
    times, states = np.asarray(ts), np.asarray(ys).T
    p, ref, sec, comp, s = states[2:].reshape(5, n, -1)
    current, q, raw, terminal = electrical(p, comp)
    internal = raw+comp
    circ = np.max(np.abs(internal[:, None, :]-internal[None, :, :]), axis=(0, 1))/(2*np.hypot(r, x))
    data = dict(time_s=times, frequency_hz=c.frequency_hz*(1+states[0]), load_mw=np.array([demand(at)/1e6 for at in times]),
                total_mw=p.sum(axis=0)/1e6, compensation_v=np.linalg.norm(comp, axis=0), circulating_a=circ)
    for j in range(n):
        for key, values in [('power_mw', p/1e6), ('soc_pct', s), ('secondary_mw', sec/1e6), ('reactive_mvar', q/1e6), ('terminal_v', terminal), ('ems_mw', ref/1e6)]:
            data[f'pcs{j+1}_{key}'] = values[j]
    return dict(config=asdict(c), columns=data, termination=termination, interpolation=interpolation, initial_soc=soc.tolist(), input_time_s=t.tolist(), input_load_mw=load.tolist())
