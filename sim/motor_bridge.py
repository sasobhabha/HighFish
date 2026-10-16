#!/usr/bin/env python3
"""Motor bridge: descending-neuron drive -> VNC leg CPG -> joint targets.

Implements the PDF spec (docs/GUIDELINES.md):
  Eq. 4: dtheta_i/dt = 2*pi*nu + sum_j w_ij(Phi) * sin(theta_j - theta_i - dphi_ij)
  Eq. 5: w_ij(Phi_GABA) = (1 - Phi_GABA) * w_ij^(0)
  Eq. 6: tau_m * da_k/dt = -a_k + sigma(sum_j w_jk_eff * r_j)
  Eq. 7: theta_target,k = theta_rest,k + a_k * dtheta_max,k

Actuator calibration (empirically verified on flygym 2.1.0 / MuJoCo 3.9, see
EXECUTION_PLAN.md): NeuroMechFly is a millimeter-scale model with gravity
-9810 mm/s^2; the library-default position servo gain (kp=1) is orders of
magnitude too weak against the passive joint springs, so the body sim builds
actuators with kp=1e5, kv=1e2. Joint roles verified by actuated probing:
  - {leg}_coxa-{leg}_trochanterfemur-pitch  -> fore-aft power stroke ( propulsion)
  - {leg}_trochanterfemur-{leg}_tibia-pitch -> knee flex (swing clearance)
  - c_thorax-{leg}_coxa-pitch               -> leg levation (lift)
Right legs are mirror-images: their stroke sign is inverted.

Scientific basis (disclosed): leg MNs/CPGs live in the VNC, which is NOT in
FAFB; the tripod CPG structure is the canonical fly gait model, and its DRIVE
comes from the FlyWire descending-neuron population rate.
"""
import numpy as np

LEGS = ["lf", "lm", "lh", "rf", "rm", "rh"]
LEGLABEL = {
    "lf": "L1", "lm": "L2", "lh": "L3",
    "rf": "R1", "rm": "R2", "rh": "R3",
}
TRIPOD1 = ["lf", "rm", "lh"]   # L1, R2, L3
TRIPOD2 = ["rf", "lm", "rh"]   # R1, L2, R3


class LegCPG:
    """6-oscillator tripod CPG (PDF Eqs. 4-5).

    nu_base=5.0 Hz with a 9 Hz cap: the cap exists for embodiment stability,
    but it must sit ABOVE baseline stepping (~3.5-4 Hz) so that stimulant
    arousal (increased descending drive) has visible headroom to speed the
    gait up, and sedation has room to slow it."""

    FREQ_CAP = 9.0

    def __init__(self, nu_base: float = 5.0):
        self.nu_base = nu_base
        # canonical tripod initial phases (tripod1 at 0, tripod2 at pi);
        # all-zero start is an unstable symmetric fixed point for antiphase lock
        self.theta = np.array([
            0.0 if LEGS[i] in TRIPOD1 else np.pi for i in range(6)
        ])
        self.dphi = np.zeros((6, 6))
        for i, li in enumerate(LEGS):
            for j, lj in enumerate(LEGS):
                same = (li in TRIPOD1) == (lj in TRIPOD1)
                self.dphi[i, j] = 0.0 if same else np.pi
        np.fill_diagonal(self.dphi, 0.0)
        self.w0 = np.zeros((6, 6))
        for i, li in enumerate(LEGS):
            for j, lj in enumerate(LEGS):
                if i == j:
                    continue
                same = (li in TRIPOD1) == (lj in TRIPOD1)
                self.w0[i, j] = 2.0 if same else 1.0

    def step(self, dt: float, drive: float, phi_gaba_block: float = 0.0):
        """drive in [0,1] sets stepping frequency; phi attenuates coupling (Eq. 5).

        Step frequency is capped at 6 Hz: flies can step faster, but the stiff
        servo + contact combination destabilizes above this in this embodiment
        (embodiment constraint)."""
        w = self.w0 * (1.0 - phi_gaba_block)
        nu = min(self.FREQ_CAP, self.nu_base * float(np.clip(drive, 0.0, 2.0)))
        dtheta = (2 * np.pi * nu
                  + np.sum(w * np.sin(self.theta[None, :] - self.theta[:, None]
                                      - self.dphi), axis=1))
        self.theta = (self.theta + dt * dtheta) % (2 * np.pi)
        return self.theta

    def tripod_sync_error(self) -> float:
        """0 when perfect tripod phase lock."""
        t1 = np.mean([self.theta[LEGS.index(l)] for l in TRIPOD1])
        t2 = np.mean([self.theta[LEGS.index(l)] for l in TRIPOD2])
        return float(abs(np.angle(np.exp(1j * (t1 - t2 + np.pi)))) / np.pi)


class MotorBridge:
    """Converts neural state + CPG phases into NMF joint targets (PDF Eqs. 6-7)."""

    # amplitudes (rad) - calibrated for mm-scale NMF (see module docstring).
    # Gait form: CONTINUOUS sine drives with the tibia lagging the femur by 90
    # deg (pawl mechanism: tibia extends during retraction to grip, flexes
    # during protraction to clear). Piecewise swing "lift" was tried and
    # rejected: the levation stroke launches the body (bouncing/flipping).
    A_STROKE = 0.80       # femur pitch stroke amplitude (stride length)
    A_KNEE = 0.50         # tibia amplitude (90 deg lag behind femur)
    TAU_M = 0.010         # PDF Eq. 6: muscle activation filter 10 ms

    # Kinematic calibration (finite-difference at the neutral keyframe,
    # d(foot_x)/d(femur_pitch), thorax-relative): a + femur pitch moves the
    # foot BACKWARD on front/mid legs (dx = -0.37 lf, -0.19 lm) but FORWARD on
    # hind legs (+0.24 lh) - the hind femur axes are reversed. Without these
    # per-leg signs the legs fight each other and the fly tumbles.
    STROKE_SIGN = {"lf": +1.0, "lm": +1.0, "lh": -1.0,
                   "rf": +1.0, "rm": +1.0, "rh": -1.0}
    # normalize stroke magnitudes (|dx|: 0.37 lf, 0.19 lm, 0.24 lh)
    STROKE_GAIN = {"lf": 1.0, "lm": 1.6, "lh": 1.3,
                   "rf": 1.0, "rm": 1.6, "rh": 1.3}

    def __init__(self, fly, actuator_dofs, rest_angles: dict[str, float]):
        self.rest = rest_angles
        self.dof_names = [d.name for d in actuator_dofs]
        self.femur: dict[str, int] = {}
        self.tibia: dict[str, int] = {}
        self.levator: dict[str, int] = {}
        self.other: list[int] = []
        for k, name in enumerate(self.dof_names):
            placed = False
            for leg in LEGS:
                if name == f"{leg}_coxa-{leg}_trochanterfemur-pitch":
                    self.femur[leg] = k
                    placed = True
                elif name == f"{leg}_trochanterfemur-{leg}_tibia-pitch":
                    self.tibia[leg] = k
                    placed = True
                elif name == f"c_thorax-{leg}_coxa-pitch":
                    self.levator[leg] = k
                    placed = True
            if not placed:
                self.other.append(k)
        self.missing = [l for l in LEGS
                        if l not in self.femur or l not in self.tibia
                        or l not in self.levator]
        self.a = {l: 0.0 for l in LEGS}
        # slew-rate limit: with kp=1e5 servos, an instantaneous large command
        # jump produces a force spike that destabilizes the solver. Must exceed
        # the CPG's max phase rate (~40 rad/s at the 6 Hz cap) or targets lag.
        self.max_target_speed = 60.0   # rad/s
        self.prev = dict(rest_angles)

    def compute_targets(self, dt: float, theta: dict[str, float],
                        mn_rate: float, para_scale: float,
                        duty_factor: float = 0.5, turn: float = 0.0) -> dict[str, float]:
        """mn_rate in [0,1] from descending drive; para_scale in (0,1];
        turn in [-1,1] biases left/right stride amplitude (steering)."""
        targets = dict(self.rest)
        amp = float(np.clip(mn_rate, 0.0, 1.0)) * para_scale
        if amp <= 1e-4:
            self.a = {l: self.a[l] * 0.9 for l in LEGS}
            self.prev = dict(targets)
            return targets
        for leg in LEGS:
            ph = theta[leg]
            # steering: turn>0 -> left legs stronger (curve left)
            side = amp * (1.0 + 0.5 * turn) if leg.startswith("l") \
                else amp * (1.0 - 0.5 * turn)
            # PDF Eq. 6: first-order muscle activation filter
            self.a[leg] += dt * (-self.a[leg] + side) / self.TAU_M
            a = self.a[leg]
            sgn = self.STROKE_SIGN[leg]
            g = self.STROKE_GAIN[leg]
            fi, ti, li = self.femur[leg], self.tibia[leg], self.levator[leg]
            # continuous strokes (no piecewise lift - see class docstring)
            fem = self.A_STROKE * a * g * sgn * np.sin(ph)
            tib = self.A_KNEE * a * g * sgn * np.sin(ph - np.pi / 2)
            targets[self.dof_names[fi]] = self.rest[self.dof_names[fi]] + fem
            targets[self.dof_names[ti]] = self.rest[self.dof_names[ti]] + tib
            # coxa pitch (levation) stays at rest; do not launch the body
        # enforce slew limit on every actuated joint
        max_step = self.max_target_speed * dt
        for k, name in enumerate(self.dof_names):
            prev_v = self.prev.get(name, targets[name])
            d = targets[name] - prev_v
            if d > max_step:
                targets[name] = prev_v + max_step
            elif d < -max_step:
                targets[name] = prev_v - max_step
        self.prev = dict(targets)
        return targets

    def mean_activation(self) -> float:
        return float(np.mean([self.a[l] for l in LEGS]))
