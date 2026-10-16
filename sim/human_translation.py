#!/usr/bin/env python3
"""Translation layer: FlyWire connectome descending neuron readout -> HumanIntent.

Scientific Provenance & Neurobiological Mapping:
  In the fruit fly (Drosophila melanogaster), the brain coordinates body movements
  by sending motor commands through ~1,305 descending neurons (DNs) that traverse
  the cervical connective into the ventral nerve cord (VNC) motor centers.
  In humans and vertebrates, the brainstem reticulospinal, vestibulospinal, and
  corticospinal tracts form the analogous descending pathway from the mesencephalic
  locomotor region (MLR), pontomedullary reticular formation, and motor cortex to
  lumbar spinal central pattern generators (CPGs) and motor neuron pools.

  This translation layer establishes a principled, neurobiologically grounded mapping
  between FlyWire connectome DN readouts + drug occupancy states and human motor intent
  (HumanIntent):

  1. Forward Propulsion Drive (forward_drive in [0, 1]):
     Mapped from total DN population activity + bilateral DNa01/DNa02 drive, minus
     inhibitory/reversal arrest signals from MDN (Moonwalker Descending Neurons).
     Corresponds to vertebrate reticulospinal locomotor drive initiating and maintaining
     locomotor velocity (Grillner 2006, Lemon 2008, Bidaye et al. 2014).

  2. Steering / Turn Intent (turn_intent in [-1, 1]):
     Mapped from asymmetric activation of lateralized descending neurons (DNa01/DNa02)
     and hemisphere DN drive, combined with stimulus turn bias. In flies, unilateral
     DNa02 activation steers walking toward the active side (Rayshubskiy et al. 2020);
     in humans, asymmetric reticulospinal and vestibulospinal activation drives heading
     changes (Drew & Marigold 2015).

  3. Coordination & Left-Right Coupling (coordination in [0, 1]):
     Derived from GABA_A / Rdl receptor occupancy (phi_gaba). In vertebrate spinal cords,
     commissural interneurons (CINs) provide reciprocal Ia inhibition (via GABA_A and glycine)
     to enforce alternating anti-phase stepping (Kiehn 2006, 2016). Suppressing GABA_A
     receptors collapses reciprocal coupling into ataxic, uncoordinated locomotion.

  4. Motor Tone & Extensor Force (motor_tone in [0, 1]):
     Derived from voltage-gated sodium channel availability (para_nav_phi, para_scale).
     Local anesthetics (e.g. Lidocaine) block axonal action potential conduction,
     reducing muscle recruitment, joint stiffness, and anti-gravity postural tone
     (bradykinesia and flaccidity; Catterall 2012).

  5. Cadence / Stepping Frequency (cadence in Hz):
     Scales human biped stepping rate (nominally 0.8 - 1.8 Hz) with arousal and forward drive.
     Modulated by dopaminergic/nicotinic wake pathways (D1-like / dDAT / nAChR) and
     attenuated by histamine/sedative blockade.

  6. Flee Urgency & Defensive Arrest (flee_drive, freeze):
     Looming visual threats (predator stimulus) trigger escape arousal via descending pathways,
     accelerating cadence and stride length, or triggering freezing if arrest signals dominate.
"""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "processed"


@dataclass
class HumanIntent:
    """High-level motor intent translated from neural and pharmacological state."""
    forward_drive: float      # [0.0, 1.0] Normalized forward propulsion command
    turn_intent: float        # [-1.0, 1.0] Yaw steering intent (-1.0 left, +1.0 right)
    cadence: float            # Stepping frequency in Hz (nominally 0.8 to 2.0 Hz)
    stride_length: float      # Target stride amplitude scale [0.0, 1.5]
    posture_height: float     # Target vertical erectness / anti-gravity tone [0.0, 1.0]
    coordination: float       # [0.0, 1.0] Left-right reciprocal phase coupling (1=clean anti-phase)
    motor_tone: float         # [0.0, 1.0] Muscle activation / force ceiling (Na_v scaling)
    flee_drive: float         # [0.0, 1.0] Urgency from looming threat stimulus
    freeze: bool              # Motor arrest flag (from MDN or severe paralysis)
    mode: str                 # "walk" | "stand" | "jog" | "ataxic" | "freeze"
    raw_signals: dict[str, Any] = field(default_factory=dict)


# Rule table defining the translation logic, mathematical equations, and provenance.
RULE_TABLE: list[dict[str, Any]] = [
    {
        "signal": "DN_pop_mean",
        "target": "forward_drive",
        "description": "Population descending neuron rate drives forward propulsion",
        "formula": "D_fwd = clip((0.7 * (R_DN / R_DN_base) + 0.3 * (R_DNa / R_DNa_base) - 1.2 * delta_R_MDN) * para_scale * arousal, 0, 1)",
        "provenance": "MLR / reticulospinal locomotor drive hypothesis (Grillner 2006; Lemon 2008; Rayshubskiy et al. 2020)",
        "citations": ["C182", "C183", "C184"],
    },
    {
        "signal": "DNa01_DNa02_asymmetry",
        "target": "turn_intent",
        "description": "Bilateral descending asymmetry and external steering bias determine yaw turning",
        "formula": "tau_turn = clip(0.7 * A_DNa + 0.3 * A_DN_hemisphere + turn_bias, -1.0, 1.0)",
        "provenance": "Ipsilateral/contralateral steering descending circuits (Rayshubskiy et al. 2020; Drew & Marigold 2015)",
        "citations": ["C184", "C185"],
    },
    {
        "signal": "GABA_A_block (rdl_phi)",
        "target": "coordination",
        "description": "GABAergic reciprocal inhibition collapse degrades left-right coordination",
        "formula": "C_biped = max(0.0, 1.0 - phi_gaba); triggers ataxic mode when C_biped < 0.55",
        "provenance": "Spinal commissural interneuron reciprocal Ia inhibition (Kiehn 2006, 2016; PDF Eq. 5)",
        "citations": ["C1", "C2", "C121", "C122"],
    },
    {
        "signal": "Na_v_block (para_nav_phi)",
        "target": "motor_tone",
        "description": "Sodium channel block reduces motor axon excitability and anti-gravity muscle tone",
        "formula": "T_motor = para_scale * min(1.0, 0.4 + 0.6 * (R_DN / R_DN_base))",
        "provenance": "Local anesthetic Na_v blockade reducing muscle force capacity (Catterall 2012; PDF Eq. 6)",
        "citations": ["C51", "C52", "C141"],
    },
    {
        "signal": "Dopamine / Nicotinic / Histamine arousal",
        "target": "cadence",
        "description": "Neuromodulatory arousal scales stepping cadence",
        "formula": "nu = nu_base * (0.6 + 0.6 * forward_drive) * arousal_gain",
        "provenance": "Monoaminergic and histaminergic modulation of locomotor speed (Oh et al. 2013; Grillner 2008)",
        "citations": ["C144", "C179", "C180"],
    },
    {
        "signal": "MDN_arrest",
        "target": "freeze",
        "description": "High Moonwalker Descending Neuron activation evokes motor arrest",
        "formula": "freeze = (R_MDN > 0.95 and R_DN < 0.4) or (forward_drive < 0.05)",
        "provenance": "Moonwalker descending neurons induce backward walking or halt forward gait (Bidaye et al. 2014)",
        "citations": ["C182", "C183"],
    },
]


class DNToHumanTranslator:
    """Translates FlyWire connectome descending neuron state into humanoid motor intent."""

    # Calibrated baseline references from unperturbed vehicle simulation
    REF_DN_RATE = 0.68          # Mean baseline DN firing rate in FlyWireNeuralSim
    REF_DNA_RATE = 0.90         # Mean baseline DNa01/02 steering neuron firing rate
    REF_MDN_RATE = 0.90         # Mean baseline MDN firing rate
    BASE_CADENCE = 1.10         # Nominal human stepping cadence (Hz, 1.10 Hz = 132 steps/min)
    BASE_STRIDE = 1.35          # Nominal human stride length scaling (m)
    BASE_POSTURE = 1.0          # Nominal posture height scale

    def __init__(self, processed_dir: Path = DATA_DIR):
        self.processed_dir = Path(processed_dir)
        df = pd.read_parquet(self.processed_dir / "neurons.parquet")
        
        # Identify descending neuron indices
        dn_mask = df["super_class"] == "descending"
        self.all_dn_idx = np.where(dn_mask)[0]
        
        # Left and Right descending populations for hemispheric asymmetry
        self.left_dn_idx = np.where(dn_mask & (df["side"] == "left"))[0]
        self.right_dn_idx = np.where(dn_mask & (df["side"] == "right"))[0]
        
        # Specific functional descending neurons
        self.dna01_left = np.where((df["primary_type"] == "DNa01") & (df["side"] == "left"))[0]
        self.dna01_right = np.where((df["primary_type"] == "DNa01") & (df["side"] == "right"))[0]
        self.dna02_left = np.where((df["primary_type"] == "DNa02") & (df["side"] == "left"))[0]
        self.dna02_right = np.where((df["primary_type"] == "DNa02") & (df["side"] == "right"))[0]
        
        # Combined steering DN indices
        dna_mask = df["primary_type"].isin(["DNa01", "DNa02"])
        self.dna_all_idx = np.where(dna_mask)[0]
        self.dna_left_idx = np.where(dna_mask & (df["side"] == "left"))[0]
        self.dna_right_idx = np.where(dna_mask & (df["side"] == "right"))[0]
        
        # Moonwalker descending neurons (arrest / reversal)
        mdn_mask = df["primary_type"] == "MDN"
        self.mdn_idx = np.where(mdn_mask)[0]

    def translate(
        self,
        neural_sim: Any,
        drug_mod: dict[str, Any] | None = None,
        stim_mgr: Any = None,
    ) -> HumanIntent:
        """Translates instantaneous neural state and drug parameters to HumanIntent.

        Args:
            neural_sim: Instance of FlyWireNeuralSim with .r (firing rates).
            drug_mod: Output from drug_modulation(drug_name, dose), containing
                      'sim_params' and 'fly_mapping'.
            stim_mgr: Optional StimulusManager for food / predator states.

        Returns:
            HumanIntent instance with calibrated motor commands.
        """
        rates = neural_sim.r
        sp = (drug_mod.get("sim_params") if drug_mod else {}) or {}

        # 1. Read descending neuron populations
        r_dn_mean = float(np.mean(rates[self.all_dn_idx])) if len(self.all_dn_idx) else self.REF_DN_RATE
        r_dn_l = float(np.mean(rates[self.left_dn_idx])) if len(self.left_dn_idx) else r_dn_mean
        r_dn_r = float(np.mean(rates[self.right_dn_idx])) if len(self.right_dn_idx) else r_dn_mean
        
        r_dna_mean = float(np.mean(rates[self.dna_all_idx])) if len(self.dna_all_idx) else self.REF_DNA_RATE
        r_dna_l = float(np.mean(rates[self.dna_left_idx])) if len(self.dna_left_idx) else r_dna_mean
        r_dna_r = float(np.mean(rates[self.dna_right_idx])) if len(self.dna_right_idx) else r_dna_mean
        
        r_mdn_mean = float(np.mean(rates[self.mdn_idx])) if len(self.mdn_idx) else self.REF_MDN_RATE

        # 2. Extract drug & neuromodulatory factors
        para_scale = float(getattr(neural_sim, "excitability_scale", 1.0))
        arousal_att = float(getattr(neural_sim, "arousal_attenuation", 1.0))
        phi_gaba = float(sp.get("rdl_phi", sp.get("gaba_phi", sp.get("phi_gaba", 0.0))))
        phi_gaba = float(np.clip(phi_gaba, 0.0, 1.0))
        
        # Arousal gain from stimulants (dopaminergic / wake drive)
        da_gain = float(sp.get("d1_like_gain", 0.0)) + float(sp.get("da_gain", 0.0))
        stimulant_gain = float(np.clip(1.0 + 0.3 * da_gain, 0.6, 1.5)) * arousal_att

        # External stimulus drives
        turn_bias = float(getattr(neural_sim, "turn_bias", 0.0))
        stim_predator = float(getattr(neural_sim, "stim_predator", 0.0))
        stim_food = float(getattr(neural_sim, "stim_food", 0.0))

        # 3. Compute Steering / Turn Intent
        # Hemispheric and DNa asymmetry: (Right - Left) / (Right + Left + eps)
        # Note: In Drosophila, right DNa02 activation steers right (ipsilateral).
        asym_dna = (r_dna_r - r_dna_l) / (r_dna_r + r_dna_l + 1e-5)
        asym_all = (r_dn_r - r_dn_l) / (r_dn_r + r_dn_l + 1e-5)
        turn_intent = float(np.clip(0.6 * asym_dna + 0.2 * asym_all + turn_bias, -1.0, 1.0))

        # 4. Compute Forward Propulsion Drive
        # Normalized by calibrated baseline references (target ~0.65 for baseline walking)
        dn_norm = r_dn_mean / max(0.1, self.REF_DN_RATE)
        dna_norm = r_dna_mean / max(0.1, self.REF_DNA_RATE)
        mdn_excess = max(0.0, (r_mdn_mean - self.REF_MDN_RATE) / max(0.1, self.REF_MDN_RATE))
        
        base_drive = 0.65 * (0.7 * dn_norm + 0.3 * dna_norm - 1.2 * mdn_excess)
        # Boost drive from food attraction or threat arousal
        base_drive += 0.25 * stim_food + 0.35 * stim_predator
        
        # Modulated by Na_v excitability and wake arousal
        forward_drive = float(np.clip(base_drive * para_scale * stimulant_gain, 0.0, 1.0))

        # 5. Compute Coordination Index (Left-Right Coupling)
        # Reciprocal inhibition scaled by GABA_A availability
        coordination = float(np.clip(1.0 - phi_gaba, 0.0, 1.0))

        # 6. Compute Motor Tone (Muscle Activation & Force Ceiling)
        # Driven by Na_v availability and general reticulospinal vigor
        motor_tone = float(np.clip(para_scale * (0.3 + 0.7 * min(1.0, dn_norm)), 0.05, 1.0))

        # 7. Compute Posture Height (Antigravity Extensor Tone)
        # Local anesthetics or severe sedation drop posture height (knee buckling)
        posture_height = float(np.clip(para_scale * min(1.0, 0.5 + 0.5 * stimulant_gain), 0.2, 1.0))

        # 8. Compute Cadence and Stride Length
        # Natural adult human cadence: 0.9 Hz to 1.8 Hz (110 - 140 steps/min)
        cad_drive = float(np.clip(forward_drive / 0.535, 0.0, 2.0))
        cadence = float(np.clip(self.BASE_CADENCE * (0.65 + 0.35 * cad_drive) * stimulant_gain, 0.5, 2.2))
        stride_length = float(np.clip(self.BASE_STRIDE * cad_drive * (0.5 + 0.5 * motor_tone), 0.0, 1.4))

        # 9. Flee Drive and Freeze Mode
        flee_drive = float(np.clip(stim_predator * stimulant_gain, 0.0, 1.0))
        freeze = bool(
            (r_mdn_mean > 0.98 and r_dn_mean < 0.35)
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
            "r_dn_mean": r_dn_mean,
            "r_dn_left": r_dn_l,
            "r_dn_right": r_dn_r,
            "r_dna_mean": r_dna_mean,
            "r_mdn_mean": r_mdn_mean,
            "para_scale": para_scale,
            "arousal_att": arousal_att,
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
    from sim.neural_sim import FlyWireNeuralSim
    from sim.drug_engine import drug_modulation

    print("Testing DNToHumanTranslator...")
    translator = DNToHumanTranslator()
    print(f"Loaded {len(translator.all_dn_idx)} DNs, {len(translator.dna_all_idx)} DNa01/02, {len(translator.mdn_idx)} MDN.")
    
    sim = FlyWireNeuralSim()
    for _ in range(50):
        sim.step()
    
    # 1. Vehicle baseline
    intent_base = translator.translate(sim)
    print("\nVehicle Baseline Intent:")
    for k, v in vars(intent_base).items():
        if k != "raw_signals":
            print(f"  {k:16s}: {v}")
            
    # 2. Lidocaine (Na_v block)
    mod_lido = drug_modulation("Lidocaine", 1.0)
    sim_lido = FlyWireNeuralSim()
    sim_lido.apply_drug(mod_lido["fly_mapping"], mod_lido["sim_params"])
    for _ in range(50):
        sim_lido.step()
    intent_lido = translator.translate(sim_lido, mod_lido)
    print("\nLidocaine Intent (Na_v block):")
    print(f"  forward_drive : {intent_lido.forward_drive:.3f} (vs {intent_base.forward_drive:.3f})")
    print(f"  motor_tone    : {intent_lido.motor_tone:.3f} (vs {intent_base.motor_tone:.3f})")
    print(f"  posture_height: {intent_lido.posture_height:.3f} (vs {intent_base.posture_height:.3f})")
    
    # 3. GABA block (Jungle Juice or synthetic rdl block)
    mod_jj = drug_modulation("Jungle Juice (Everything mixed)", 1.0)
    intent_jj = translator.translate(sim, mod_jj)
    print("\nJungle Juice Intent:")
    print(f"  coordination  : {intent_jj.coordination:.3f}")
    print(f"  mode          : {intent_jj.mode}")
