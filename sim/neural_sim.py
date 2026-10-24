#!/usr/bin/env python3
"""Neural simulation over the Fish1 larval zebrafish connectome (Petkova et al. 2025).

Pipeline:
  sensory/arousal stimulus drive -> E/I-resolved rate dynamics on the 876k-cell
  zebrafish adjacency -> hindbrain (reticulospinal-like) population readout.

Equations (docs/GUIDELINES.md):
  Eq. 2: g_syn(t) = (1 - Phi) * g_max * s(t)      [drug scaling of synaptic drive]
  Eq. 3: ds/dt = -s/tau_decay + presynaptic drive  [synaptic gating variable]
  Rate model: dr/dt = (-r + phi(x)) / tau_r,  x = W_E r - W_I r + I(t)

ALL connectivity comes from data/processed (created by
scripts/extract_fish1_syns.py + scripts/parse_fishconnectome.py):
- adj_E.npz / adj_I.npz: polarity-weighted excitatory / inhibitory adjacency.
  E/I polarity is NOT guessed: it is the Fish1 `_ei_bayes` layer's `type` code,
  verified against CLEM cell identification (vglut2a -> type 2, gad1b -> type 1;
  see data/processed/meta.json -> ei_semantics).
- neurons.parquet: per-cell stats incl. nt_pred, ap_norm/lr_norm, roi.

Drug interface: receptor-system mapping dict from data/pharmacology.yaml
(zebrafish systems; every mapping is citation-backed).
"""
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA = ROOT_DIR / "data" / "processed"


class ZebrafishNeuralSim:
    """E/I-resolved rate-network over the larval zebrafish connectome."""

    def __init__(self, processed_dir: Path = DATA):
        self.meta = json.loads((processed_dir / "meta.json").read_text())
        adjE = sp.load_npz(processed_dir / "adj_E.npz")
        adjI = sp.load_npz(processed_dir / "adj_I.npz")
        assert adjE.shape == adjI.shape
        self.n = adjE.shape[0]

        # log1p scale then normalize to the 99th percentile of each polarity's
        # weights (modeling choice, same as the previous connectome sim)
        self.wE = self._scale(adjE)
        self.wI = self._scale(adjI)

        self.tau_r = 0.02          # rate time constant (s)
        self.tau_s = 0.01          # Eq. 3 synaptic decay ~10 ms
        self.dt = 1e-3             # neural integration step (s)
        self.rng = np.random.default_rng(0)

        # per-cell metadata (parquet row order == adjacency row order)
        import pandas as pd
        df = pd.read_parquet(processed_dir / "neurons.parquet")
        assert len(df) == self.n, (len(df), self.n)
        self.cell_id = df["cell_id"].to_numpy()
        self.nt_pred = df["nt_pred"].to_numpy()
        self.frac_out_E = df["frac_out_E"].to_numpy()
        self.ap_norm = df["ap_norm"].to_numpy()
        self.lr_norm = df["lr_norm"].to_numpy()
        self.roi = df["roi"].to_numpy()
        self.n_out_syn = df["n_out_syn"].to_numpy()
        self.n_in_syn = df["n_in_syn"].to_numpy()

        # ---- populations ----
        # stimulus drive: anterior+central neurons (sensory / thalamic-ish drive)
        stim_mask = (self.roi != "hindbrain") & (self.n_in_syn >= 10)
        self.stim_idx = np.where(stim_mask)[0]
        left = self.lr_norm < -0.25
        right = self.lr_norm > 0.25
        self.stim_idx_left = np.where(stim_mask & left)[0]
        self.stim_idx_right = np.where(stim_mask & right)[0]
        self.central_idx = np.where(self.roi == "central")[0].astype(int)
        # hindbrain readout pool: posterior-half cells that are properly
        # embedded (sufficient incoming AND outgoing synapses) with the
        # strongest outputs - reticulospinal-like descending population.
        # Data-derived threshold (the hindbrain pool is 2,961 cells; >=10 out /
        # >=5 in synapses keeps 187 well-embedded descending candidates without
        # discarding well-connected mid-strength cells).
        hb_mask = ((self.roi == "hindbrain")
                   & (self.n_out_syn >= 10)
                   & (self.n_in_syn >= 5))
        self.readout_idx = np.where(hb_mask)[0]

        # external stimulus state (set by StimulusManager via apply_stim)
        self.stim_food = 0.0        # prey-attraction drive
        self.stim_predator = 0.0    # looming intensity -> arousal/escape drive
        self.turn_bias = 0.0        # steering signal

        # state
        self.r = np.full(self.n, 0.05, dtype=np.float32)
        self.s = np.zeros(self.n, dtype=np.float32)

        # drug state (multiplicative occupancy / additive gains, like the
        # previous connectome sim; no behavioral outcome knobs)
        self.occupancy = {"E": 0.0, "I": 0.0}   # synaptic-block occupancy per polarity
        self.gain_E = 0.0                        # excitatory drive gain (agonists)
        self.gain_I = 0.0                        # inhibitory drive gain
        self.gain_mod = 0.0                      # modulatory (GPCR) network gain
        self.excitability_scale = 1.0  # Nav block scales achievable rate
        self.arousal_attenuation = 1.0  # H1-block / sedation-like drive cut
        self.drive_scale = 1.0

        self.stim_rate = 0.6      # in-range of the phi transfer (phi(0.6)~0.82): modulation must be able to move rates
        self.rng.shuffle(self.stim_idx)

    # ---------------- setup helpers ----------------
    def _scale(self, adj: sp.csr_matrix) -> sp.csr_matrix:
        a = adj.copy()
        a.data = np.log1p(np.maximum(a.data, 0.0)).astype(np.float32)
        nz = a.data[a.data > 0]
        # scale by the MEAN nonzero value: the fish1 graph is extremely sparse (mean
        # degree ~6), so p99 scaling leaves the
        # network quiescent. Mean scaling gives a typical edge ~O(1) weight.
        scale = float(nz.mean()) if nz.size else 1.0
        a = (a / scale).astype(np.float32)
        a.data = np.clip(a.data, 0.0, 2.0)
        return a.tocsr()

    # ---------------- external stimuli (prey / predator) ----------------
    def apply_stim(self, food_gain: float = 0.0, predator_intensity: float = 0.0,
                   turn_bias: float = 0.0):
        """Set per-step external stimulus drives (from sim/stimuli.py)."""
        self.stim_food = food_gain
        self.stim_predator = predator_intensity
        self.turn_bias = turn_bias

    # ---------------- drug interface (from data/pharmacology.yaml) ----------
    def apply_drug(self, mapping: dict, sim_params: dict):
        """mapping: zebrafish receptor system -> {direction}; sim_params YAML.
        Parameter lookup is exact-name first, so YAML sim_params are
        authoritative. No behavioral outcome knobs anywhere - behavior must
        EMERGE from receptor-level parameters on the connectome dynamics."""
        # synaptic occupancies
        occ_map = {
            "gaba_a": "gaba_a_phi",          # inhibitory synapse block (diphenhydramine-adjacent targets live here only if cited)
            "glyr": "glyr_phi",              # glycine-gated chloride
            "nachr": "nachr_phi",            # nicotinic ACh (excitatory iontropic)
            "glut_iontropic": "glut_iontropic_phi",  # AMPA/NMDA block
            "cnr1": "cnr1_phi",              # CB1 (GABA-terminal predominant)
        }
        for system, key in occ_map.items():
            if system in mapping:
                direction = str(mapping[system].get("direction", ""))
                match = ("antagonist" in direction or "blocker" in direction
                         or "negative" in direction)
                if system == "cnr1":
                    # THC is a CB1 AGONIST but its sim-relevant effect is the
                    # same presynaptic-release reduction (see above)
                    match = match or "agonist" in direction
                if match:
                    phi = float(sim_params.get(key, 0.0))
                    if system in ("gaba_a", "glyr"):
                        self.occupancy["I"] = min(1.0, self.occupancy["I"] + phi)
                    elif system == "cnr1":
                        # CB1 on presynaptic terminals reduces transmitter
                        # release; in zebrafish CB1 activation lowers brain GABA
                        # (Lachowicz 2023) -> model as reduced inhibitory drive
                        self.occupancy["I"] = min(1.0, self.occupancy["I"] + phi)
                    elif system == "nachr":
                        self.occupancy["E"] = min(1.0, self.occupancy["E"] + phi)
                    else:
                        self.occupancy["E"] = min(1.0, self.occupancy["E"] + phi)

        # GABA_A positive allosteric modulation (benzodiazepines; Cao 2019 /
        # Moradi-Afrapoli 2017): does NOT occupy the orthosteric site - it
        # increases postsynaptic GABA sensitivity, i.e. the EFFECTIVE inhibitory
        # drive. Modeled as increased inhibitory gain (opposite sign of block).
        if "gaba_a" in mapping:
            direction = str(mapping["gaba_a"].get("direction", ""))
            if "positive_allosteric" in direction:
                phi = float(sim_params.get("gaba_a_pam_phi", 0.0))
                self.gain_I += 0.9 * phi

        # agonist / positive-modulation gains per system
        if "nachr" in mapping:
            direction = str(mapping["nachr"].get("direction", ""))
            if "agonist" in direction:
                self.gain_E += float(sim_params.get("nachr_gain", 0.0)
                                     or sim_params.get("nachr_activation_gain", 0.0))
        for system, key in (("adora", "adora_gain"), ("htr", "ser_gain"),
                            ("d1_like", "da_gain"), ("machr", "machr_gain"),
                            ("htr_5ht2", "htr2_gain")):
            if system in mapping and key in sim_params:
                setattr(self, "_apply_mod_gain", None)
                self.gain_mod += float(sim_params[key]) if system != "adora" else 0.0

        # adenosine host: A1/A2A antagonists (caffeine) are arousal-promoting
        if "adora" in mapping:
            direction = str(mapping["adora"].get("direction", ""))
            if "antagonist" in direction:
                phi = float(sim_params.get("adora_phi", 0.0))
                # behavioral data: caffeine INCREASES locomotor activity and
                # arousal (Maximino 2011; Wei 2024) -> model as arousal drive boost
                self.arousal_boost = getattr(self, "arousal_boost", 0.0) + 1.2 * phi
            if "agonist" in direction:  # adenosine = sleep pressure
                phi = float(sim_params.get("adora_phi", 0.0))
                self.drive_scale *= (1.0 - 0.5 * phi)

        # dopamine reuptake (slc6a3 DAT)
        if "dat" in mapping:
            direction = str(mapping["dat"].get("direction", ""))
            if "inhibitor" in direction or "substrate" in direction:
                phi = float(sim_params.get("dat_phi", 0.0))
                self.gain_mod += 0.8 * phi          # slow modulatory gain
                self.arousal_boost = getattr(self, "arousal_boost", 0.0) + 1.0 * phi

        # 5-HT receptors (mirtazapine antagonism, CBD partial agonism, APAP)
        if "htr" in mapping:
            self.gain_mod += float(sim_params.get("ser_gain", 0.0))

        # histamine H1 (first-gen antihistamines): wake-axis attenuation
        if "hrh1" in mapping:
            direction = str(mapping["hrh1"].get("direction", ""))
            if "antagonist" in direction or "blocker" in direction:
                phi = float(sim_params.get("hrh1_phi", 0.0))
                self.arousal_attenuation *= (1.0 - 0.5 * phi)

        # muscarinic (anticholinergic component of diphenhydramine etc.)
        if "machr" in mapping:
            direction = str(mapping["machr"].get("direction", ""))
            if "antagonist" in direction:
                self.gain_mod -= 0.3 * float(sim_params.get("machr_phi", 0.0))

        # voltage-gated Nav (scn1lab equivalent channel; lidocaine / TTX-lidocaine)
        if "nav" in mapping:
            phi = float(sim_params.get("nav_phi", 0.0))
            self.excitability_scale *= max(0.05, 1.0 - 0.8 * phi)

        # serotonin transporter (sert / slc6a4a-4b; fluoxetine, C199-C202):
        # reuptake inhibition raises extracellular 5-HT -> acute serotonergic
        # gain, with a mild arousal attenuation (high-dose hypoactivity signal)
        if "sert" in mapping:
            direction = str(mapping["sert"].get("direction", ""))
            if "inhibitor" in direction:
                phi = float(sim_params.get("sert_phi", 0.0))
                self.gain_mod += 0.8 * phi
                self.arousal_attenuation *= (1.0 - 0.25 * phi)

        # melatonin receptors (mtnr; Gandhi 2015 / Zhdanova 2001): sleep-promoting
        # axis -> arousal attenuation + reduced net drive scale (the same shape
        # the adenosine-agonist sleep-pressure arm uses)
        if "mtnr" in mapping:
            direction = str(mapping["mtnr"].get("direction", ""))
            if "agonist" in direction:
                phi = float(sim_params.get("mtnr_phi", 0.0))
                self.arousal_attenuation *= (1.0 - 0.55 * phi)
                self.drive_scale *= (1.0 - 0.35 * phi)

        # dopamine D2-family receptors (d2_like; haloperidol, Irons 2013 /
        # Oliveri 2019): antagonists DECREASE larval locomotor activity ->
        # dopaminergic arousal attenuation + reduced motor-vigor gain
        if "d2_like" in mapping:
            direction = str(mapping["d2_like"].get("direction", ""))
            if "antagonist" in direction:
                phi = float(sim_params.get("d2_phi", 0.0))
                self.arousal_attenuation *= (1.0 - 0.6 * phi)
                self.gain_mod -= 0.4 * phi

        # acetylcholinesterase inhibition (donepezil; Giacomini 2020) elevates
        # synaptic ACh acting on mAChR/nAChR -> positive cholinergic modulation
        if "ache" in mapping:
            direction = str(mapping["ache"].get("direction", ""))
            if "inhibitor" in direction:
                self.gain_mod += 0.5 * float(sim_params.get("ache_phi", 0.0))

    # ---------------- dynamics ----------------
    def _phi(self, x: np.ndarray) -> np.ndarray:
        # gentler operating point than the old connectome sim: the fish1 graph
        # is sparse (mean degree ~6), so a low-center, moderate-slope transfer
        # is needed for drive to propagate to the posterior readout
        return 1.0 / (1.0 + np.exp(-np.clip(6.0 * (x - 0.25), -30.0, 30.0)))

    def step(self, stimulus: float | None = None):
        dt = self.dt
        acc = np.zeros(self.n, dtype=np.float32)
        acc += ((1.0 - self.occupancy["E"]) * (1.0 + max(self.gain_E, 0.0))) * (self.wE.T @ self.r)
        acc -= ((1.0 - self.occupancy["I"]) * (1.0 + max(self.gain_I, 0.0))) * (self.wI.T @ self.r)
        if self.gain_mod:
            # modulatory GPCR gain applied positively on the net drive
            acc *= (1.0 + self.gain_mod)

        drive = self.stim_rate * self.drive_scale * self.arousal_attenuation
        drive *= (1.0 + getattr(self, "arousal_boost", 0.0))
        # global wake-axis scaling: sedation-like attenuation scales the net
        # synaptic input to ALL cells (wake-promoting histamine axis), while
        # the local stim drive above already carries the stimulus structure
        acc *= (1.0 - 0.6 * (1.0 - getattr(self, "arousal_attenuation", 1.0)))
        if stimulus is not None:
            drive *= stimulus
        drive = min(drive, 1.4)   # cap arousal (saturation guard)
        if len(self.stim_idx):
            k = min(len(self.stim_idx), 50000)
            acc[self.stim_idx[:k]] += drive
        if self.turn_bias != 0:
            bias = float(np.clip(self.turn_bias, -1.0, 1.0))
            k_lat = min(1500, len(self.stim_idx_right), len(self.stim_idx_left))
            if k_lat > 0:
                if bias > 0:
                    acc[self.stim_idx_right[:k_lat]] += bias * drive * 0.9
                    acc[self.stim_idx_left[:k_lat]] -= bias * drive * 0.4
                else:
                    acc[self.stim_idx_left[:k_lat]] += (-bias) * drive * 0.9
                    acc[self.stim_idx_right[:k_lat]] -= (-bias) * drive * 0.4
        if self.stim_food > 0 and len(self.central_idx):
            acc[self.central_idx] += self.stim_food
        if self.stim_predator > 0:
            acc += self.stim_predator * 0.8
        acc += self.rng.normal(0, 0.02, self.n).astype(np.float32)

        r_target = self._phi(acc) * self.excitability_scale
        self.r += dt * (r_target - self.r) / self.tau_r
        self.r = np.clip(self.r, 0.0, 1.0)

        self.s += dt * (-self.s / self.tau_s + self.r)
        self.s = np.clip(self.s, 0.0, 2.0)

    # ---------------- outputs ----------------
    def readout_output(self) -> float:
        """Mean activity of the hindbrain reticulospinal-like readout pool."""
        if len(self.readout_idx) == 0:
            return 0.0
        return float(np.mean(self.r[self.readout_idx]))

    def population_summary(self) -> dict:
        out = {}
        for roi_name in ("anterior", "central", "hindbrain"):
            idx = np.where(self.roi == roi_name)[0]
            out[roi_name] = float(np.mean(self.r[idx])) if len(idx) else 0.0
        # E/I split
        e_i = np.where(self.frac_out_E >= 0.5)[0]
        i_i = np.where(self.frac_out_E < 0.5)[0]
        out["exc"] = float(np.mean(self.r[e_i])) if len(e_i) else 0.0
        out["inh"] = float(np.mean(self.r[i_i])) if len(i_i) else 0.0
        out["readout"] = self.readout_output()
        return out


def load_readout_indices(processed_dir: Path = DATA) -> np.ndarray:
    """Indices of the hindbrain (reticulospinal-like) readout pool (fallback)."""
    import pandas as pd
    df = pd.read_parquet(processed_dir / "neurons.parquet",
                         columns=["roi", "n_out_syn", "n_in_syn"])
    hb = np.where((df["roi"].to_numpy() == "hindbrain"))[0]
    q = np.percentile(df["n_out_syn"].to_numpy()[hb], 75) if len(hb) else 0
    out = hb[df["n_out_syn"].to_numpy()[hb] >= q]
    order = np.argsort(-df["n_out_syn"].to_numpy()[out])
    return out[order[: max(1, int(0.05 * len(out)))]] if len(out) else out


if __name__ == "__main__":
    sim = ZebrafishNeuralSim()
    print(f"neurons: {sim.n:,}; stim populations: {len(sim.stim_idx):,}; "
          f"readout pool: {len(sim.readout_idx):,}")
    for _ in range(300):
        sim.step()
    print("baseline:", {k: round(v, 4) for k, v in sim.population_summary().items()})
    sim.apply_drug(
        mapping={"nachr": {"direction": "agonist_then_desensitization"},
                 "nav": {"direction": "blocker"}},
        sim_params={"nav_phi": 0.7, "nachr_gain": 0.3},
    )
    for _ in range(300):
        sim.step()
    print("post-drug (tobacco+lidocaine-like):",
          {k: round(v, 4) for k, v in sim.population_summary().items()})
