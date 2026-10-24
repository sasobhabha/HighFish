#!/usr/bin/env python3
"""Translation layer: zebrafish connectome hindbrain readout -> HumanIntent.

Scientific Provenance & Neurobiological Mapping:
  In the larval zebrafish (Danio rerio), the brain coordinates body movements by
  sending motor commands through hindbrain reticulospinal neurons (the
  homologs of the human pontomedullary reticulospinal tract) that descend into
  the spinal cord motor centers. In humans and vertebrates, the reticulospinal,
  vestibulospinal, and corticospinal tracts form the analogous descending
  pathway from the mesencephalic locomotor region (MLR), pontomedullary
  reticular formation, and motor cortex to lumbar central pattern generators
  (CPGs) and motor neuron pools.

  The mapping here is DIRECT: motion-intent parameters are computed from the
  ZebrafishNeuralSim hindbrain (reticulospinal-like) readout pool rates plus
  the drug-conditioned receptor parameters - no species-specific matrices:

  1. Forward Propulsion Drive (forward_drive in [0, 1]):
     Mapped from the hindbrain readout pool activity (reticulospinal-like,
     Grillner 2006; Lemon 2008; Koyama et al. 2016 for zebrafish hindbrain
     visuomotor descending control; Dragatsikas 2026 for whole-brain dynamics).
     Boosted by prey-attraction (stim_food) and looming escape arousal
     (stim_predator).

  2. Steering / Turn Intent (turn_intent in [-1, 1]):
     Mapped from lateralized asymmetry of the stimulated (sensory/arousal)
     pools, combined with stimulus turn bias (ZEbrafish prey-tracking is
     driven by bilateral tectal/sensory asymmetries; Dombeck 2013 hypotheses
     apply analogously here).

  3. Coordination & Left-Right Coupling (coordination in [0, 1]):
     Derived from left/right symmetry of the hindbrain readout halves, scaled
     DOWN by GABAergic inhibitory block occupancy (phi_gaba). In the vertebrate
     spinal cord, commissural interneurons (CINs) provide reciprocal inhibition
     (GABA_A and glycine) to enforce alternating anti-phase stepping; PTZ-like
     GABA_A block collapses reciprocal coupling into uncoordinated locomotion
     (Kiehn 2006, 2016). Suppressed lateral symmetry is an emergent network
     property on the fish connectome, so no explicit GABA adjacency matrix is used.

  4. Motor Tone & Extensor Force (motor_tone in [0, 1]):
     Derived from voltage-gated sodium channel availability (nav_phi ->
     excitability_scale). Local anesthetics (Lidocaine) block axonal action
     potential conduction, reducing muscle recruitment, joint stiffness, and
     anti-gravity postural tone (Catterall 2012; also supported by the larval
     zebrafish scn1lab (Nav1.1) mutant phenotype - motor-skill degeneration).

  5. Cadence / Stepping Frequency (cadence in Hz):
     Scales biped stepping rate (nominally 0.8-1.8 Hz) with arousal and
     forward drive; modulated by dopaminergic / nicotinic / adenosine wake
     pathways (maximino 2011; Wei 2024 for caffeine locomotion in zebrafish)
     and attenuated by histamine H1 / sedative block.
"""
from dataclasses import dataclass, field
import sys
from typing import Any

import numpy as np

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class HumanIntent:
    """High-level motor intent translated from neural and pharmacological state."""
    forward_drive: float      # [0.0, 1.0] Normalized forward propulsion command
    turn_intent: float        # [-1.0, 1.0] Yaw steering intent (-1.0 left, +1.0 right)
    cadence: float            # Stepping frequency in Hz (nominally 0.8 to 2.0 Hz)
    stride_length: float      # Target stride amplitude scale [0.0, 1.5]
    posture_height: float     # Target vertical erectness / anti-gravity tone [0.0, 1.0]
    coordination: float       # [0.0, 1.0] Left-right reciprocal phase coupling
    motor_tone: float         # [0.0, 1.0] Muscle activation / force ceiling (Na_v scaling)
    flee_drive: float         # [0.0, 1.0] Urgency from looming threat stimulus
    freeze: bool              # Motor arrest flag (from arrest signal or paralysis)
    mode: str                 # "walk" | "stand" | "jog" | "ataxic" | "freeze"
    raw_signals: dict[str, Any] = field(default_factory=dict)


# Rule table defining the translation logic, mathematical equations, and provenance.
RULE_TABLE: list[dict[str, Any]] = [
    {
        "signal": "hindbrain_readout_mean",
        "target": "forward_drive",
        "description": "Hindbrain (reticulospinal-like) pool rate drives forward propulsion",
        "formula": "D_fwd = clip((0.7 * (R_RO / R_RO_base) + 0.3 * 1.0) * 0.65 + 0.25*stim_food + 0.35*stim_predator) * nav_scale * arousal, 0, 1)",
        "provenance": "Hindbrain reticulospinal locomotor drive (Grillner 2006; Koyama 2016; Dragatsikas 2026)",
    },
    {
        "signal": "stim_pool_asymmetry",
        "target": "turn_intent",
        "description": "Lateralized sensory-pool asymmetry and external steering bias determine yaw turning",
        "formula": "tau_turn = clip(0.6 * A_stim_lateral + 0.4 * turn_bias, -1.0, 1.0)",
        "provenance": "Zebrafish hindbrain visuomotor steering (Koyama 2016; sens. driftmap, Dragatsikas 2026)",
    },
    {
        "signal": "GABA_block (phi_gaba via occupancy['I'])",
        "target": "coordination",
        "description": "GABAergic reciprocal inhibition collapse degrades left-right coordination",         "formula": "C_biped = clip(LR_symmetry * (1.0 - 0.60 * phi_gaba), 0, 1); "
                    "triggers ataxic mode when C_biped < 0.55 (habat 0.85 occupancy "
                    "collapses coordination to ~0.49)",
        "provenance": "Spinal commissural interneuron reciprocal inhibition (Kiehn 2006, 2016)",
    },
    {
        "signal": "Na_v_block (nav_phi)",
        "target": "motor_tone",
        "description": "Sodium channel block reduces motor axon excitability and anti-gravity muscle tone",
        "formula": "T_motor = nav_scale * min(1.0, 0.4 + 0.6 * (R_RO / R_RO_base))",
        "provenance": "Local anesthetic Na_v blockade reducing muscle force capacity (Catterall 2012)",
    },
    {
        "signal": "Dopamine / Nicotinic / Adenosine arousal",
        "target": "cadence",
        "description": "Neuromodulatory arousal scales stepping cadence",
        "formula": "nu = nu_base * (0.65 + 0.35 * forward_drive / 0.65) * arousal_gain",
        "provenance": "Monoaminergic / adenosine modulation of zebrafish locomotor speed (Maximino 2011; Wei 2024)",
    },
    {
        "signal": "readout_rate_collapse",
        "target": "freeze",
        "description": "Readout rate collapse or near-paralysis evokes motor arrest",
        "formula": "freeze = (R_RO > 1.4*R_RO_base and D_fwd < 0.1) or (D_fwd < 0.03 and stim_predator > 0.5) or (motor_tone < 0.10)",
        "provenance": "Zebrafish arrest/gait-collapse analogues (Dragatsikas 2026; Kiehn 2016)",
    },
]


class ZebrafishReadout:
    """Translates ZebrafishNeuralSim hindbrain readout state into humanoid motor intent."""

    # Calibrated baseline references from unperturbed vehicle simulation
    REF_RO_RATE = 0.18          # Mean baseline hindbrain readout firing rate
    REF_STIM_RATE = 0.20        # Reference lateral stim-pool firing rate (asymmetry ref)
    BASE_CADENCE = 1.10         # Nominal human stepping cadence (Hz, 1.10 Hz = 132 steps/min)
    BASE_STRIDE = 1.35          # Nominal human stride length scaling (m)

    def __init__(self, processed_dir=None):
        # The readout pool lives on the sim itself; expose the same alias for
        # pipeline compatibility with the old translator interface.
        self.all_dn_idx = np.zeros(0, np.int64)

    def translate(
        self,
        neural_sim: Any,
        drug_mod: dict[str, Any] | None = None,
        stim_mgr: Any = None,
    ) -> HumanIntent:
        """Translates instantaneous neural state and drug parameters to HumanIntent."""
        rates = neural_sim.r
        ro_idx = getattr(neural_sim, "readout_idx", self.all_dn_idx)

        # 1. Read hindbrain readout pool populations (whole + left/right halves)
        r_ro_mean = float(np.mean(rates[ro_idx])) if len(ro_idx) else self.REF_RO_RATE
        if len(ro_idx) >= 2 and hasattr(neural_sim, "lr_norm"):
            lr = neural_sim.lr_norm[ro_idx]
            li = np.where(lr < 0)[0]
            ri = np.where(lr >= 0)[0]
            r_ro_l = float(np.mean(rates[ro_idx[li]])) if len(li) else r_ro_mean
            r_ro_r = float(np.mean(rates[ro_idx[ri]])) if len(ri) else r_ro_mean
        else:
            r_ro_l = r_ro_r = r_ro_mean

        # lateral asymmetry of the stimulated (sensory/arousal) pools
        stim_l = getattr(neural_sim, "stim_idx_left", None)
        stim_r = getattr(neural_sim, "stim_idx_right", None)
        if stim_l is not None and stim_r is not None and len(stim_l) and len(stim_r):
            r_l = float(np.mean(rates[stim_l[: min(20000, len(stim_l))]]))
            r_r = float(np.mean(rates[stim_r[: min(20000, len(stim_r))]]))
            asym_stim = (r_r - r_l) / (r_r + r_l + 1e-5)
        else:
            r_l = r_r = 0.0
            asym_stim = 0.0

        # 2. Extract drug & neuromodulatory factors
        nav_scale = float(getattr(neural_sim, "excitability_scale", 1.0))
        arousal_att = float(getattr(neural_sim, "arousal_attenuation", 1.0))
        drive_scale = float(getattr(neural_sim, "drive_scale", 1.0))
        arousal_boost = float(getattr(neural_sim, "arousal_boost", 0.0))
        gain_E = float(getattr(neural_sim, "gain_E", 0.0))
        occ = getattr(neural_sim, "occupancy", {"I": 0.0})
        phi_gaba = float(np.clip(occ.get("I", 0.0), 0.0, 1.0))

        # Arousal gain from stimulants (dopaminergic / nicotinic / adenosine wake)
        da_gain = float(np.clip((drive_scale - 1.0) + 0.5 * gain_E + 0.5 * arousal_boost,
                                0.0, 2.0))
        stimulant_gain = float(np.clip(1.0 + 0.3 * da_gain, 0.6, 1.5)) * arousal_att

        # External stimulus drives (set by StimulusManager via apply_stim)
        turn_bias = float(getattr(neural_sim, "turn_bias", 0.0))
        stim_predator = float(getattr(neural_sim, "stim_predator", 0.0))
        stim_food = float(getattr(neural_sim, "stim_food", 0.0))

        # 3. Compute Steering / Turn Intent
        # Lateral stim-pool asymmetry + external steering bias
        turn_intent = float(np.clip(0.6 * asym_stim + 0.4 * turn_bias, -1.0, 1.0))

        # 4. Compute Forward Propulsion Drive
        # Normalized by calibrated baseline reference (target ~0.65 at baseline)
        ro_norm = r_ro_mean / max(0.05, self.REF_RO_RATE)
        base_drive = 0.65 * (0.7 * ro_norm + 0.3 * 1.0)
        base_drive += 0.25 * stim_food + 0.35 * stim_predator
        forward_drive = float(np.clip(base_drive * nav_scale * stimulant_gain, 0.0, 1.0))

        # 5. Compute Coordination Index (Left-Right Coupling)
        # Emergent readout-pool lateral symmetry, degraded by GABAergic block
        mm = max(r_ro_l, r_ro_r, 1e-6)
        lr_sym = 1.0 - abs(r_ro_l - r_ro_r) / mm
        coordination = float(np.clip(lr_sym * (1.0 - 0.60 * phi_gaba), 0.0, 1.0))

        # 6. Compute Motor Tone (Muscle Activation & Force Ceiling)
        motor_tone = float(np.clip(nav_scale * (0.3 + 0.7 * min(1.0, ro_norm)),
                                   0.05, 1.0))

        # 7. Compute Posture Height (Antigravity Extensor Tone)
        posture_height = float(np.clip(
            nav_scale * min(1.0, 0.5 + 0.5 * stimulant_gain) * min(1.0, lr_sym + 0.3),
            0.2, 1.0))

        # 8. Compute Cadence and Stride Length
        cad_drive = float(np.clip(forward_drive / 0.535, 0.0, 2.0))
        cadence = float(np.clip(self.BASE_CADENCE * (0.65 + 0.35 * cad_drive)
                                * stimulant_gain, 0.5, 2.2))
        stride_length = float(np.clip(self.BASE_STRIDE * cad_drive
                                      * (0.5 + 0.5 * motor_tone), 0.0, 1.4))

        # 9. Flee Drive and Freeze Mode
        flee_drive = float(np.clip(stim_predator * stimulant_gain, 0.0, 1.0))
        freeze = bool(
            (r_ro_mean > 1.4 * self.REF_RO_RATE and forward_drive < 0.10)
            or (forward_drive < 0.03 and stim_predator > 0.5)
            or (motor_tone < 0.10)
        )

        # 10. Classify Gait Mode
        if freeze:
            mode = "freeze"
        elif coordination < 0.55:
            mode = "ataxic"
        elif forward_drive < 0.10 or stride_length < 0.05:
            mode = "stand"
        elif forward_drive > 0.85:
            mode = "jog"
        else:
            mode = "walk"

        raw_signals = {
            "r_ro_mean": r_ro_mean,
            "r_ro_left": r_ro_l,
            "r_ro_right": r_ro_r,
            "r_stim_left": r_l,
            "r_stim_right": r_r,
            "nav_scale": nav_scale,
            "arousal_att": arousal_att,
            "drive_scale": drive_scale,
            "arousal_boost": arousal_boost,
            "phi_gaba": phi_gaba,
            "stimulant_gain": stimulant_gain,
            "stim_food": stim_food,
            "stim_predator": stim_predator,
            "turn_bias": turn_bias,
        }

        return HumanIntent(
            forward_drive=forward_drive,
            turn_intent=turn_intent,
            cadence=cadence,
            stride_length=stride_length,
            posture_height=posture_height,
            coordination=coordination,
            motor_tone=motor_tone,
            flee_drive=flee_drive,
            freeze=freeze,
            mode=mode,
            raw_signals=raw_signals,
        )


if __name__ == "__main__":
    from sim.neural_sim import ZebrafishNeuralSim
    from sim.drug_engine import drug_modulation

    print("Testing ZebrafishReadout...")
    translator = ZebrafishReadout()
    print(f"Readout pool: (from sim; alias size {len(translator.all_dn_idx)}).")

    sim = ZebrafishNeuralSim()
    translator.all_dn_idx = sim.readout_idx
    for _ in range(300):
        sim.step()

    # 1. Vehicle baseline
    intent_base = translator.translate(sim)
    print("\nVehicle Baseline Intent:")
    for k, v in vars(intent_base).items():
        if k != "raw_signals":
            print(f"  {k:16s}: {v}")

    # 2. Lidocaine (Na_v block)
    mod_lido = drug_modulation("Lidocaine", 1.0)
    sim_lido = ZebrafishNeuralSim()
    translator_lido = ZebrafishReadout()
    translator_lido.all_dn_idx = sim_lido.readout_idx
    sim_lido.apply_drug(mod_lido["fish_mapping"], mod_lido["sim_params"])
    for _ in range(300):
        sim_lido.step()
    intent_lido = translator_lido.translate(sim_lido, mod_lido)
    print("\nLidocaine Intent (Na_v block):")
    print(f"  forward_drive : {intent_lido.forward_drive:.3f} (vs {intent_base.forward_drive:.3f})")
    print(f"  motor_tone    : {intent_lido.motor_tone:.3f} (vs {intent_base.motor_tone:.3f})")
    print(f"  posture_height: {intent_lido.posture_height:.3f} (vs {intent_base.posture_height:.3f})")

    # 3. GABAergic block (multi-receptor product)
    mod_ptz = drug_modulation("Jungle Juice (Everything mixed)", 1.0)
    sim_ptz = ZebrafishNeuralSim()
    translator_ptz = ZebrafishReadout()
    translator_ptz.all_dn_idx = sim_ptz.readout_idx
    sim_ptz.apply_drug(mod_ptz["fish_mapping"], mod_ptz["sim_params"])
    for _ in range(300):
        sim_ptz.step()
    intent_ptz = translator_ptz.translate(sim_ptz, mod_ptz)
    print("\nJungle Juice Intent (GABA block, multi-receptor):")
    print(f"  coordination  : {intent_ptz.coordination:.3f}")
    print(f"  mode          : {intent_ptz.mode}")
