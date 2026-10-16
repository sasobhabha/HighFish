#!/usr/bin/env python3
"""Neural simulation over the FlyWire v783 connectome.

Pipeline (documented in EXECUTION_PLAN.md):
  sensory/optic stimulus drive -> brain-wide rate dynamics on the FlyWire adjacency
  -> descending neuron (DN) population output -> VNC leg CPGs (motor_bridge).

Equations follow docs/GUIDELINES.md (PDF spec):
  Eq. 2: g_syn(t) = (1 - Phi) * g_max * s(t)      [drug scaling of synaptic drive]
  Eq. 3: ds/dt = -s/tau_decay + presynaptic drive  [synaptic gating variable]
  Rate model (simplification of the PDF's LIF option; dt=1e-3 here vs
  1e-4 physics - rates change slowly, documented in EXECUTION_PLAN.md):
      dr/dt = (-r + phi(x)) / tau_r,  x = W_nt @ r + I(t) + b
  where W_nt is the NT-resolved adjacency with per-NT sign and drug occupancy:
      W_eff[nt] = (1 - Phi_nt) * w_nt        (antagonist)
      W_eff[nt] = (1 + gain_nt) * w_nt        (agonist / positive modulation)

ALL connectivity comes from data/processed/adj_*.npz (FlyWire codex v783).
Neuron identity and NT predictions are FlyWire's.
"""
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA = ROOT_DIR / "data" / "processed"


class FlyWireNeuralSim:
    """Rate-network over the FlyWire brain connectome with drug modulation."""

    def __init__(self, processed_dir: Path = DATA):
        self.meta = json.loads((processed_dir / "meta.json").read_text())
        self.adj_total = sp.load_npz(processed_dir / "adj_total.npz").tocsr()
        self.n = self.adj_total.shape[0]
        self.nt_adjs = {}
        for nt in ("ACH", "GABA", "GLUT", "DA", "SER", "OCT"):
            p = processed_dir / f"adj_{nt}.npz"
            if p.exists():
                self.nt_adjs[nt] = sp.load_npz(p).tocsr()
        # per-NT sign (FlyWire NT identity -> functional polarity)
        # ACH excitatory; GABA inhibitory; GLUT mixed (modeled weakly excitatory
        # at ionotropic receptors; modeling choice); modulators small +.
        self.nt_sign = {
            "ACH": +1.0, "GABA": -1.0, "GLUT": +0.3, "DA": +0.2, "SER": +0.2, "OCT": +0.2,
        }
        # log-scaled weights normalized by the 99th percentile of nonzero counts
        # (raw counts span 1..1000+; log scaling keeps strong edges strong while
        # letting weak edges still contribute - modeling choice)
        self.w = {}
        for nt, adj in self.nt_adjs.items():
            a = adj.copy()
            a.data = np.log1p(a.data)
            nz = a.data[a.data > 0]
            scale = np.percentile(nz, 99) if nz.size else 1.0
            a_scaled = (a / scale).astype(np.float32)
            a_scaled.data = np.clip(a_scaled.data, -1.5, 1.5)
            self.w[nt] = a_scaled * self.nt_sign[nt]

        self.tau_r = 0.02          # rate time constant (s), 5x physics dt regime
        self.tau_s = 0.01          # PDF Eq. 3 synaptic decay ~10 ms
        self.dt = 1e-3             # neural integration step (s)
        self.rng = np.random.default_rng(0)

        # external stimulus state (set by StimulusManager via apply_stim)
        self.stim_food = 0.0        # attraction drive (odor plume proxy)
        self.stim_predator = 0.0    # looming intensity -> arousal/escape drive
        self.turn_bias = 0.0        # steering signal (read by motor bridge)

        # state
        self.r = np.full(self.n, 0.05, dtype=np.float32)
        self.s = np.zeros(self.n, dtype=np.float32)

        # drug state: per-NT multiplicative occupancy (1 = no drug)
        self.occupancy = {nt: 0.0 for nt in self.nt_adjs}
        self.gains = {nt: 0.0 for nt in self.nt_adjs}
        self.global_gain = 0.0
        self.excitability_scale = 1.0  # para_nav block scales max rate
        self.drive_scale = 1.0         # sedation-like scale on external drive
        # histamine wake-axis attenuation (Oh et al. 2013, C144: the
        # histamine-HisCl1 axis ACTIVATES AND MAINTAINS WAKE; blocking it
        # increases sleep). Set by apply_drug for ort_histamine antagonists.
        self.arousal_attenuation = 1.0
        self.descending_gain = 1.0     # applied to DN output pooling

        # stimulus: sparse stochastic drive into sensory/optic populations
        sc = np.array(self.meta["super_class_counts"])
        self.super_class, self.side = self._load_metadata(processed_dir)
        stim_mask = np.isin(self.super_class, ["sensory", "optic", "visual_projection"])
        self.stim_idx = np.where(stim_mask)[0]
        self.stim_idx_left = np.where(stim_mask & (self.side == "left"))[0]
        self.stim_idx_right = np.where(stim_mask & (self.side == "right"))[0]
        self.central_idx = np.where(self.super_class == "central")[0]
        self.stim_rate = 1.2           # baseline drive magnitude
        self.rng.shuffle(self.stim_idx)

    # ---------------- external stimuli (food / predator) ----------------
    def apply_stim(self, food_gain: float = 0.0, predator_intensity: float = 0.0,
                   turn_bias: float = 0.0):
        """Set per-step external stimulus drives (from sim/stimuli.py)."""
        self.stim_food = food_gain
        self.stim_predator = predator_intensity
        self.turn_bias = turn_bias

    @staticmethod
    def _load_metadata(processed_dir: Path) -> tuple[np.ndarray, np.ndarray]:
        import pandas as pd

        df = pd.read_parquet(processed_dir / "neurons.parquet", columns=["super_class", "side"])
        return df["super_class"].to_numpy(), df["side"].to_numpy()

    # ---------------- drug interface (from data/pharmacology.yaml) -------------
    def apply_drug(self, mapping: dict, sim_params: dict):
        """mapping: fly receptor system -> {direction}; sim_params from YAML.

        Parameter lookup order is exact-name first (e.g. ort_histamine_phi),
        so YAML sim_params are authoritative.        Disclosed model for histamine: ort/HisCl1 are histamine-gated
        CHLORIDE channels, but histamine is NOT a codex NT (no matrix to
        block), and applying its block to the GABA matrix would wrongly block
        every GABAergic synapse (that is Rdl pharmacology, not HisCl1).
        Correct model (cited): the histamine-HisCl1 axis ACTIVATES AND
        MAINTAINS WAKE (Oh 2013, C144), so its block attenuates the arousal
        (sensory) drive -> drowsiness EMERGES as reduced network drive. No
        outcome knob anywhere.
        """
        # 1) occupancies (antagonist-like)
        occ_map = {
            "nachr": ("ACH", "nachr_phi"),
            "rdl": ("GABA", "rdl_phi"),
            "glut_iontropic": ("GLUT", "glut_iontropic_phi"),
        }
        for system, (nt, key) in occ_map.items():
            if system in mapping:
                direction = mapping[system].get("direction", "")
                if "antagonist" in direction or "blocker" in direction:
                    self.occupancy[nt] = min(1.0, self.occupancy[nt]
                                             + float(sim_params.get(key, 0.0)))
        # 2) transporter/reuptake (ddat): less DA clearance -> DA gain up
        if "ddat" in mapping:
            self.gains["DA"] += 0.5 * float(sim_params.get("ddat_phi", 0.0))
        # 3) receptor gains
        if "nachr" in mapping and "nachr_activation_gain" in sim_params:
            self.gains["ACH"] += float(sim_params["nachr_activation_gain"])
        if "d1_like" in mapping and "d1_like_gain" in sim_params:
            self.gains["DA"] += float(sim_params["d1_like_gain"])
        if "5ht_receptors" in mapping and "ser_gain" in sim_params:
            self.gains["SER"] += float(sim_params["ser_gain"])
        if "da_gain" in sim_params:
            self.gains["DA"] += float(sim_params["da_gain"])
        # 4) excitability (para Nav block) - scales achievable firing rate
        if "para_nav" in mapping:
            phi = float(sim_params.get("para_nav_phi", 0.0))
            self.excitability_scale *= max(0.05, 1.0 - 0.8 * phi)
        # 5) histamine wake-axis (systems level, Oh et al. 2013 C144): blocking
        #    the wake-promoting HisCl1 axis attenuates arousal drive. Drowsy
        #    behavior (slower stepping, sluggish responses) then EMERGES from
        #    the network dynamics on the connectome.
        if "ort_histamine" in mapping:
            direction = mapping["ort_histamine"].get("direction", "")
            if "antagonist" in direction or "blocker" in direction:
                phi = float(sim_params.get("ort_histamine_phi", 0.0))
                self.arousal_attenuation *= (1.0 - 0.5 * phi)
        # 5) global scalars. NOTE: no per-drug behavioral outcome knobs -
        # behavior must EMERGE from the receptor-level parameters above
        # (occupancy on NT matrices, transporter/reuptake, receptor gains,
        # excitability). 

    # ---------------- dynamics ----------------
    def _phi(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(20.0 * (x - 0.5), -30.0, 30.0)))

    def step(self, stimulus: float | None = None):
        dt = self.dt
        # effective weights: (1 - Phi) for blocked NTs, (1 + gain) for modulated
        acc = np.zeros(self.n, dtype=np.float32)
        for nt, w in self.w.items():
            scale = (1.0 - self.occupancy.get(nt, 0.0)) * (1.0 + self.gains.get(nt, 0.0))
            acc += (w.T @ self.r) * scale
        # stimulus
        drive = self.stim_rate * self.drive_scale * self.arousal_attenuation
        if stimulus is not None:
            drive *= stimulus
        drive = min(drive, 3.5)   # cap arousal: >~5 saturates all rates -> tetanic leg drive -> hopping
        if len(self.stim_idx):
            k = min(2000, len(self.stim_idx))
            acc[self.stim_idx[:k]] += drive
        # asymmetric visual steering drive into bilateral sensory/optic populations
        if self.turn_bias != 0 and hasattr(self, "stim_idx_right") and hasattr(self, "stim_idx_left"):
            bias = float(np.clip(self.turn_bias, -1.0, 1.0))
            k_lat = min(1500, len(self.stim_idx_right), len(self.stim_idx_left))
            if k_lat > 0:
                if bias > 0:
                    acc[self.stim_idx_right[:k_lat]] += bias * drive * 0.9
                    acc[self.stim_idx_left[:k_lat]] -= bias * drive * 0.4
                else:
                    acc[self.stim_idx_left[:k_lat]] += (-bias) * drive * 0.9
                    acc[self.stim_idx_right[:k_lat]] -= (-bias) * drive * 0.4
        # food attraction: weak excitatory drive into central circuits
        if self.stim_food > 0 and len(self.central_idx):
            acc[self.central_idx] += self.stim_food
        # predator looming: strong arousal/escape drive (global excitation)
        if self.stim_predator > 0:
            acc += self.stim_predator * 0.8
        # noise
        acc += self.rng.normal(0, 0.02, self.n).astype(np.float32)
        acc *= (1.0 + self.global_gain)

        # rate dynamics
        r_target = self._phi(acc) * self.excitability_scale
        self.r += dt * (r_target - self.r) / self.tau_r
        self.r = np.clip(self.r, 0.0, 1.0)

        # synaptic gating (PDF Eq. 3): ds/dt = -s/tau + drive
        self.s += dt * (-self.s / self.tau_s + self.r)
        self.s = np.clip(self.s, 0.0, 2.0)

    # ---------------- outputs ----------------
    def descending_output(self, dn_indices: np.ndarray) -> float:
        """Mean activity of descending neurons (FAFB DNs, super_class=='descending')."""
        if len(dn_indices) == 0:
            return 0.0
        return float(np.mean(self.r[dn_indices]))

    def population_summary(self) -> dict:
        out = {}
        for sc_name in ("sensory", "optic", "central", "visual_projection",
                        "descending", "ascending", "motor"):
            idx = np.where(self.super_class == sc_name)[0]
            out[sc_name] = float(np.mean(self.r[idx])) if len(idx) else 0.0
        return out


def load_dn_indices(processed_dir: Path = DATA) -> np.ndarray:
    import pandas as pd

    df = pd.read_parquet(processed_dir / "neurons.parquet", columns=["super_class"])
    return np.where(df["super_class"] == "descending")[0]


if __name__ == "__main__":
    sim = FlyWireNeuralSim()
    print(f"neurons: {sim.n:,}; stim populations: {len(sim.stim_idx):,}")
    dn = load_dn_indices()
    print(f"descending neurons (FAFB DNs): {len(dn):,}")
    for i in range(300):
        sim.step()
    print("baseline population summary:",
          {k: round(v, 4) for k, v in sim.population_summary().items()})
    print(f"DN output at baseline: {sim.descending_output(dn):.4f}")
    sim.apply_drug(
        mapping={"nachr": {"direction": "agonist_then_desensitization"},
                 "para_nav": {"direction": "blocker"}},
        sim_params={"para_nav_phi": 0.7},
    )
    for i in range(300):
        sim.step()
    print("post-drug (tobacco+lidocaine-like) summary:",
          {k: round(v, 4) for k, v in sim.population_summary().items()})
    print(f"DN output post-drug: {sim.descending_output(dn):.4f}")
