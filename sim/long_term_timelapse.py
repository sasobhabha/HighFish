#!/usr/bin/env python3
"""Long-Term Pharmacokinetics, Chronobiology, & Sleep Homeostasis Timelapse Engine.

Simulates and visualizes the true multi-hour physiological progression of drugs:
1. 2-Compartment / 1-Compartment Pharmacokinetics (absorption, distribution, clearance, half-life).
2. Two-Process Model of Sleep Regulation (Borbély):
   - Process S: Homeostatic sleep debt / adenosine buildup across waking hours.
   - Process C: 24-hour circadian arousal oscillation.
3. Pharmacodynamic Adaptation:
   - Caffeine: Adenosine receptor masking + dopamine arousal -> sustained hyperactivity ->
               metabolic clearance -> sudden unmasking of accumulated sleep debt (THE CAFFEINE CRASH).
   - Dormiphen (Diphenhydramine): H1 blockade -> rapid sedation peak -> sleep latency drop ->
                                  gradual metabolic clearance -> morning grogginess resolution.
   - Lidocaine: Acute Na_v block (flaccid paralysis) -> hepatic CYP1A2 clearance (t1/2=1.8h) ->
                gradual motor tone restoration and upright walking recovery.
   - Nicotine: Fast peak -> rapid nAChR desensitization -> clearance.
   - Vyvanse / Methamphetamine: Prolonged dopaminergic surge (t1/2=11h) -> delayed crash.

Visual Timelapse Output:
- Stroboscopic embodied 3D MuJoCo probes across a 12h or 24h timeline.
- High-definition HUD telemetry overlay (time elapsed, plasma concentration, sleep debt,
  perceived fatigue, forward walking speed, and physiological state).
- Exports continuous cinematic MP4 / GIF timelapse videos and structured JSON telemetry.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.drug_engine import load_pharmacology, drug_modulation
from sim.human_pipeline import HumanPipelineSim
from sim.stimuli import StimulusConfig


# =====================================================================
# 1. Pharmacokinetic & Chronobiological Parameters (Literature-Backed)
# =====================================================================

@dataclass
class DrugPKPDProfile:
    name: str
    t_half_elim_h: float      # Elimination half-life in hours
    t_half_abs_h: float       # Absorption half-life in hours
    t_max_h: float            # Time to peak plasma concentration
    tau_tolerance_h: float    # Receptor desensitization / acute tolerance time constant
    beta_tolerance: float     # Tolerance strength factor
    masking_power: float      # Ability to mask Process S sleep debt (caffeine / stimulants)
    sedation_power: float     # Direct somnogenic / sedative drive (antihistamines / hypnotics)
    motor_block_power: float  # Peripheral / central motor block (local anesthetics)

# Verified PK/PD parameter catalog
PK_PROFILES: dict[str, DrugPKPDProfile] = {
    "Caffeine": DrugPKPDProfile(
        name="Caffeine",
        t_half_elim_h=5.0,        # Human CYP1A2 t1/2 ~ 4.5-5.5h (zebrafish ~4.0h)
        t_half_abs_h=0.25,        # Fast oral absorption (~15-20 min)
        t_max_h=0.75,             # Peak plasma conc at 45 min
        tau_tolerance_h=3.5,      # Acute receptor adaptation
        beta_tolerance=0.35,
        masking_power=0.85,       # Potent adenosine receptor masking
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Dormiphen (Sleeping Pill)": DrugPKPDProfile(
        name="Dormiphen (Sleeping Pill)",
        t_half_elim_h=8.5,        # Diphenhydramine t1/2 ~ 7.0-9.5h
        t_half_abs_h=0.50,        # Peak sedative onset ~ 1-2 hours
        t_max_h=2.0,              # Tmax ~ 2 hours
        tau_tolerance_h=6.0,
        beta_tolerance=0.20,
        masking_power=0.0,
        sedation_power=0.90,      # Potent central H1 inverse agonism / sedation
        motor_block_power=0.15,   # Minor anticholinergic sluggishness
    ),
    "Claritin (Tablet)": DrugPKPDProfile(
        name="Claritin (Tablet)",
        t_half_elim_h=8.0,        # Loratadine t1/2 ~ 8h (active metabolite ~28h)
        t_half_abs_h=0.50,
        t_max_h=1.5,
        tau_tolerance_h=12.0,
        beta_tolerance=0.10,
        masking_power=0.0,
        sedation_power=0.15,      # 2nd generation: minimal CNS penetration
        motor_block_power=0.0,
    ),
    "Lidocaine": DrugPKPDProfile(
        name="Lidocaine",
        t_half_elim_h=1.8,        # Hepatic clearance t1/2 ~ 1.5-2.0h
        t_half_abs_h=0.10,        # Immediate local / systemic distribution
        t_max_h=0.30,             # Fast peak (~20 min)
        tau_tolerance_h=2.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.20,
        motor_block_power=0.95,   # Profound voltage-gated Na_v conduction block
    ),
    "Tobacco": DrugPKPDProfile(
        name="Tobacco",
        t_half_elim_h=2.0,        # Nicotine t1/2 ~ 1.5-2.0h
        t_half_abs_h=0.05,        # Rapid pulmonary/mucosal uptake (<5 min)
        t_max_h=0.15,
        tau_tolerance_h=0.40,     # Extremely fast nAChR desensitization (20-30 min)
        beta_tolerance=1.20,
        masking_power=0.40,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Tobacco Extract": DrugPKPDProfile(
        name="Tobacco Extract",
        t_half_elim_h=2.0,
        t_half_abs_h=0.05,
        t_max_h=0.15,
        tau_tolerance_h=0.40,
        beta_tolerance=1.20,
        masking_power=0.40,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Vyvanse": DrugPKPDProfile(
        name="Vyvanse",
        t_half_elim_h=11.0,       # Lisdexamfetamine -> d-amphetamine t1/2 ~ 10-12h
        t_half_abs_h=1.20,        # Enzymatic rate-limited cleavage in RBCs
        t_max_h=3.5,              # Tmax ~ 3.5h
        tau_tolerance_h=8.0,
        beta_tolerance=0.30,
        masking_power=0.95,       # Sustained monoaminergic arousal
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Jungle Juice (Everything mixed)": DrugPKPDProfile(
        name="Jungle Juice (Everything mixed)",
        t_half_elim_h=6.0,
        t_half_abs_h=0.30,
        t_max_h=1.0,
        tau_tolerance_h=3.0,
        beta_tolerance=0.50,
        masking_power=0.50,
        sedation_power=0.85,
        motor_block_power=0.75,
    ),
    "Weed": DrugPKPDProfile(
        name="Weed",
        t_half_elim_h=20.0,
        t_half_abs_h=0.20,
        t_max_h=0.50,
        tau_tolerance_h=8.0,
        beta_tolerance=0.30,
        masking_power=0.10,
        sedation_power=0.55,
        motor_block_power=0.25,
    ),
    "CBD nanodrops": DrugPKPDProfile(
        name="CBD nanodrops",
        t_half_elim_h=24.0,
        t_half_abs_h=1.0,
        t_max_h=2.5,
        tau_tolerance_h=12.0,
        beta_tolerance=0.10,
        masking_power=0.0,
        sedation_power=0.25,
        motor_block_power=0.05,
    ),
    "Mirtazapine": DrugPKPDProfile(
        name="Mirtazapine",
        t_half_elim_h=22.0,
        t_half_abs_h=0.80,
        t_max_h=2.0,
        tau_tolerance_h=12.0,
        beta_tolerance=0.15,
        masking_power=0.0,
        sedation_power=0.75,
        motor_block_power=0.20,
    ),
    "Acetaminophen": DrugPKPDProfile(
        name="Acetaminophen",
        t_half_elim_h=2.5,
        t_half_abs_h=0.30,
        t_max_h=0.75,
        tau_tolerance_h=4.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.10,
        motor_block_power=0.0,
    ),
    "Lithium Acetate": DrugPKPDProfile(
        name="Lithium Acetate",
        t_half_elim_h=24.0,
        t_half_abs_h=1.0,
        t_max_h=3.0,
        tau_tolerance_h=24.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.20,
        motor_block_power=0.10,
    ),
    "Robax": DrugPKPDProfile(
        name="Robax",
        t_half_elim_h=2.0,
        t_half_abs_h=0.30,
        t_max_h=1.0,
        tau_tolerance_h=3.0,
        beta_tolerance=0.15,
        masking_power=0.0,
        sedation_power=0.45,
        motor_block_power=0.45,
    ),
    "Bupropion (Wellbutrin)": DrugPKPDProfile(
        name="Bupropion (Wellbutrin)",
        t_half_elim_h=14.0,
        t_half_abs_h=0.80,
        t_max_h=3.0,
        tau_tolerance_h=8.0,
        beta_tolerance=0.25,
        masking_power=0.75,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Dimenhydrinate (Gravol)": DrugPKPDProfile(
        name="Dimenhydrinate (Gravol)",
        t_half_elim_h=8.0,
        t_half_abs_h=0.50,
        t_max_h=2.0,
        tau_tolerance_h=6.0,
        beta_tolerance=0.20,
        masking_power=0.10,
        sedation_power=0.85,
        motor_block_power=0.20,
    ),
    "Claritin (Gel)": DrugPKPDProfile(
        name="Claritin (Gel)",
        t_half_elim_h=8.0,
        t_half_abs_h=0.50,
        t_max_h=1.5,
        tau_tolerance_h=12.0,
        beta_tolerance=0.10,
        masking_power=0.0,
        sedation_power=0.15,
        motor_block_power=0.0,
    ),
    # ===== literature-expanded neuropharmacology catalog (2026) =====
    "Pentylenetetrazol (PTZ)": DrugPKPDProfile(
        name="Pentylenetetrazol (PTZ)",
        t_half_elim_h=2.0,        # rapid elimination after acute exposure
        t_half_abs_h=0.10,
        t_max_h=0.30,
        tau_tolerance_h=1.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.0,
        motor_block_power=0.0,    # proconvulsant: hyperexcitability, not motor block
    ),
    "Picrotoxin": DrugPKPDProfile(
        name="Picrotoxin",
        t_half_elim_h=2.5,
        t_half_abs_h=0.10,
        t_max_h=0.40,
        tau_tolerance_h=1.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Strychnine": DrugPKPDProfile(
        name="Strychnine",
        t_half_elim_h=12.0,       # human strychnine elimination ~10-16h
        t_half_abs_h=0.20,
        t_max_h=1.0,
        tau_tolerance_h=4.0,
        beta_tolerance=0.10,
        masking_power=0.0,
        sedation_power=0.0,
        motor_block_power=0.30,   # coordination collapse, not flaccid block
    ),
    "Diazepam": DrugPKPDProfile(
        name="Diazepam",
        t_half_elim_h=43.0,       # human diazepam t1/2 ~ 20-50h (+ desmethyldiazepam)
        t_half_abs_h=0.30,
        t_max_h=1.2,
        tau_tolerance_h=10.0,
        beta_tolerance=0.25,
        masking_power=0.0,
        sedation_power=0.90,      # GABA_A PAM - strong sedative
        motor_block_power=0.10,
    ),
    "Ethanol (Alcohol)": DrugPKPDProfile(
        name="Ethanol (Alcohol)",
        t_half_elim_h=1.0,        # near-zero-order elimination in the practical range
        t_half_abs_h=0.20,
        t_max_h=0.50,
        tau_tolerance_h=2.0,
        beta_tolerance=0.30,
        masking_power=0.10,
        sedation_power=0.50,      # dose-dependent CNS depressant
        motor_block_power=0.35,   # cerebellar gait ataxia
    ),
    "Ketamine": DrugPKPDProfile(
        name="Ketamine",
        t_half_elim_h=2.5,        # human ketamine t1/2 ~ 2-3h
        t_half_abs_h=0.15,
        t_max_h=0.40,
        tau_tolerance_h=1.5,
        beta_tolerance=0.40,
        masking_power=0.20,
        sedation_power=0.45,
        motor_block_power=0.20,
    ),
    "Cocaine": DrugPKPDProfile(
        name="Cocaine",
        t_half_elim_h=0.8,        # human cocaine t1/2 ~ 0.5-1h
        t_half_abs_h=0.05,
        t_max_h=0.25,
        tau_tolerance_h=0.5,
        beta_tolerance=0.60,
        masking_power=0.90,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Methylphenidate (Ritalin)": DrugPKPDProfile(
        name="Methylphenidate (Ritalin)",
        t_half_elim_h=2.5,        # human MPH t1/2 ~ 2-3h
        t_half_abs_h=0.40,
        t_max_h=1.5,
        tau_tolerance_h=2.0,
        beta_tolerance=0.30,
        masking_power=0.90,
        sedation_power=0.0,
        motor_block_power=0.0,
    ),
    "Fluoxetine (Prozac)": DrugPKPDProfile(
        name="Fluoxetine (Prozac)",
        t_half_elim_h=96.0,       # human fluoxetine t1/2 ~ 4-6 days (+ norfluoxetine)
        t_half_abs_h=1.5,
        t_max_h=6.0,
        tau_tolerance_h=24.0,
        beta_tolerance=0.20,
        masking_power=0.10,
        sedation_power=0.25,
        motor_block_power=0.10,
    ),
    "Haloperidol": DrugPKPDProfile(
        name="Haloperidol",
        t_half_elim_h=20.0,       # human haloperidol t1/2 ~ 14-36h
        t_half_abs_h=0.80,
        t_max_h=3.0,
        tau_tolerance_h=16.0,
        beta_tolerance=0.15,
        masking_power=0.0,
        sedation_power=0.30,
        motor_block_power=0.40,   # extrapyramidal motor suppression
    ),
    "Melatonin": DrugPKPDProfile(
        name="Melatonin",
        t_half_elim_h=0.75,       # human melatonin t1/2 ~ 30-60 min
        t_half_abs_h=0.25,
        t_max_h=0.75,
        tau_tolerance_h=2.0,
        beta_tolerance=0.20,
        masking_power=0.0,
        sedation_power=0.85,      # sleep-promoting axis
        motor_block_power=0.0,
    ),
    "Donepezil (Aricept)": DrugPKPDProfile(
        name="Donepezil (Aricept)",
        t_half_elim_h=70.0,       # human donepezil t1/2 ~ 70h
        t_half_abs_h=2.0,
        t_max_h=4.0,
        tau_tolerance_h=24.0,
        beta_tolerance=0.10,
        masking_power=0.10,
        sedation_power=0.10,
        motor_block_power=0.05,
    ),
    "Tetrodotoxin": DrugPKPDProfile(
        name="Tetrodotoxin",
        t_half_elim_h=2.0,        # renal elimination; human intoxication window ~ hours
        t_half_abs_h=0.10,
        t_max_h=0.35,
        tau_tolerance_h=1.0,
        beta_tolerance=0.05,
        masking_power=0.0,
        sedation_power=0.0,
        motor_block_power=1.00,   # full Nav conduction block (paralysis)
    ),
}


DEFAULT_PROFILE = DrugPKPDProfile(
    name="Vehicle control",
    t_half_elim_h=4.0,
    t_half_abs_h=0.5,
    t_max_h=1.0,
    tau_tolerance_h=4.0,
    beta_tolerance=0.2,
    masking_power=0.0,
    sedation_power=0.0,
    motor_block_power=0.0,
)


# =====================================================================
# 2. Continuous Chronobiological & Pharmacodynamic Trajectory Engine
# =====================================================================

@dataclass
class ChronoState:
    t_hours: float
    plasma_conc: float          # C(t) in [0, 1]
    effective_effect: float     # C(t) / (1 + beta*Tol)
    tolerance: float            # Receptor adaptation index
    process_s: float            # Homeostatic sleep debt [0, 1]
    process_c: float            # Circadian alertness modulation [-0.2, +0.2]
    perceived_fatigue: float    # Unmasked / realized fatigue [0, 1]
    net_arousal_gain: float     # Scaling on neural sensory & motor drive
    para_scale: float           # Excitability scaling from Na_v block [0.2, 1.0]
    walk_speed_m_s: float       # Predicted forward walking velocity
    cadence_hz: float           # Stepping frequency
    posture_height: float       # Posture height index (1.0 = erect, <0.7 = buckling)
    state_label: str            # Clinical/behavioral state descriptor


class LongTermPKPDEngine:
    """Computes continuous timecourses of drug concentration, sleep pressure, and motor state."""

    def __init__(self, drug_name: str | None = None, dose: float = 1.0):
        from sim.drug_engine import resolve_drug_name
        self.drug_name = resolve_drug_name(drug_name)
        self.dose = float(np.clip(dose, 0.0, 1.0))
        self.profile = PK_PROFILES.get(self.drug_name, DEFAULT_PROFILE)


        # Rate constants
        self.ke = np.log(2.0) / max(0.1, self.profile.t_half_elim_h)
        self.ka = np.log(2.0) / max(0.05, self.profile.t_half_abs_h)
        if abs(self.ka - self.ke) < 1e-4:
            self.ka += 0.05

        # Normalization factor so peak C(t) == dose
        t_peak = np.log(self.ka / self.ke) / (self.ka - self.ke)
        peak_raw = np.exp(-self.ke * t_peak) - np.exp(-self.ka * t_peak)
        self.pk_norm = (1.0 / peak_raw) if peak_raw > 1e-6 else 1.0

    def compute_state(self, t_hours: float) -> ChronoState:
        """Evaluates physiological state at an exact point in time (in hours)."""
        t = max(0.0, float(t_hours))

        # 1. Pharmacokinetics: Two-compartment oral absorption & elimination
        if self.drug_name in ("Vehicle control", "Vehicle", None) or self.dose <= 1e-4:
            conc = 0.0
        else:
            raw_c = np.exp(-self.ke * t) - np.exp(-self.ka * t)
            conc = float(np.clip(self.dose * self.pk_norm * raw_c, 0.0, 1.0))

        # 2. Receptor Tolerance & Desensitization (integrated approximation)
        tau_tol = self.profile.tau_tolerance_h
        # Tol(t) lags concentration:
        tol = conc * (1.0 - np.exp(-t / max(0.1, tau_tol)))
        effective_effect = conc / (1.0 + self.profile.beta_tolerance * tol)

        # 3. Two-Process Sleep Regulation Model (Borbély 1982, Daan 1984)
        # Process S: Homeostatic sleep pressure accumulates with waking time
        # Baseline wake starts at S0 = 0.15, rises asymptotically toward 1.0 with tau = 18.2h
        tau_wake = 18.2
        process_s = float(1.0 - (1.0 - 0.15) * np.exp(-t / tau_wake))

        # Process C: 24h Circadian rhythm (alertness peak at ~14:00, nadir at ~04:00)
        process_c = float(0.15 * np.cos(2.0 * np.pi * (t - 14.0) / 24.0))

        # Baseline physiological fatigue (without drug)
        fatigue_base = float(np.clip(process_s - process_c, 0.0, 1.0))

        # 4. Drug Interactions with Sleep Debt & Arousal
        # A. Stimulants (Caffeine, Vyvanse): Mask Process S via adenosine antagonism & dopamine
        masking = float(self.profile.masking_power * effective_effect)
        # B. Sedatives (Dormiphen): Directly exacerbate sleep pressure via central H1 block
        sedation = float(self.profile.sedation_power * effective_effect)
        # C. Peripheral / Central Na_v Block (Lidocaine):
        motor_block = float(self.profile.motor_block_power * effective_effect)

        # Realized / Perceived Fatigue:
        perceived_fatigue = float(np.clip(fatigue_base - masking + sedation, 0.0, 1.0))

        # 5. Net Arousal & Motor Translation
        if self.profile.masking_power > 0:
            # Stimulant timeline:
            # - While effective_effect is high: arousal is boosted (+30%), masking sleep debt
            # - As drug clears, masking vanishes while accumulated Process S hits suddenly (THE CRASH)
            stim_boost = 0.35 * effective_effect
            crash_penalty = 0.55 * max(0.0, perceived_fatigue - 0.25)
            net_arousal = float(np.clip(1.0 + stim_boost - crash_penalty, 0.35, 1.45))
        elif self.profile.sedation_power > 0:
            # Sedative timeline: heavy suppression during peak, slow clearing
            net_arousal = float(np.clip(1.0 - 0.75 * perceived_fatigue, 0.20, 1.05))
        else:
            # Normal diurnal wakefulness / slight fatigue
            net_arousal = float(np.clip(1.0 - 0.40 * perceived_fatigue, 0.50, 1.05))

        # Motor excitability (Lidocaine recovery)
        para_scale = float(np.clip(1.0 - 0.76 * motor_block, 0.24, 1.0))

        # 6. Biomechanical Outputs (Speed, Cadence, Posture)
        base_speed = 1.255  # Normal adult human walking speed in m/s
        base_cadence = 1.10 # Normal adult cadence in Hz

        walk_speed = float(np.clip(base_speed * net_arousal * (para_scale / 1.0), 0.02, 1.55))
        cadence = float(np.clip(base_cadence * (0.6 + 0.4 * net_arousal), 0.55, 1.40))
        posture_height = float(np.clip(para_scale * (1.0 - 0.35 * max(0.0, perceived_fatigue - 0.5)), 0.35, 1.0))

        # 7. Descriptive State Label
        if motor_block > 0.40:
            state_label = "MOTOR COLLAPSE (Na_v Block)"
        elif conc > 0.60 and self.profile.masking_power > 0.5:
            state_label = "HYPERACTIVE / AROUSED"
        elif conc < 0.25 and t > 4.5 and self.profile.masking_power > 0.5 and perceived_fatigue > 0.45:
            state_label = "CAFFEINE CRASH (Rebound Debt)"
        elif sedation > 0.40 or perceived_fatigue > 0.70:
            state_label = "HEAVILY SEDATED / DROWSY"
        elif perceived_fatigue > 0.45:
            state_label = "FATIGUED (Sleep Debt Accumulating)"
        elif t < 1.0 and conc < 0.30 and self.dose > 0:
            state_label = "ABSORPTION / ONSET"
        else:
            state_label = "NORMAL STEADY LOCOMOTION"

        return ChronoState(
            t_hours=round(t, 2),
            plasma_conc=round(conc, 4),
            effective_effect=round(effective_effect, 4),
            tolerance=round(tol, 4),
            process_s=round(process_s, 4),
            process_c=round(process_c, 4),
            perceived_fatigue=round(perceived_fatigue, 4),
            net_arousal_gain=round(net_arousal, 4),
            para_scale=round(para_scale, 4),
            walk_speed_m_s=round(walk_speed, 4),
            cadence_hz=round(cadence, 4),
            posture_height=round(posture_height, 4),
            state_label=state_label,
        )


# =====================================================================
# 3. HUD Visual Overlay & Cinematic Timelapse Video Assembler
# =====================================================================

def draw_timelapse_hud(
    frame_rgb: np.ndarray,
    state: ChronoState,
    drug_name: str,
    dose: float,
    checkpoint_idx: int,
    total_checkpoints: int,
) -> np.ndarray:
    """Draws a scientific HUD overlay onto an RGB simulation frame."""
    img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size

    # 1. Top Header Banner (Translucent Dark Charcoal)
    draw.rectangle([0, 0, width, 54], fill=(12, 16, 24, 210))
    # Bottom Telemetry Bar
    draw.rectangle([0, height - 44, width, height], fill=(12, 16, 24, 220))

    # Determine state color
    if "COLLAPSE" in state.state_label:
        badge_bg = (220, 38, 38, 230)      # Crimson
    elif "HYPERACTIVE" in state.state_label:
        badge_bg = (14, 165, 233, 230)     # Sky Cyan
    elif "CRASH" in state.state_label:
        badge_bg = (217, 119, 6, 230)      # Amber / Orange
    elif "SEDATED" in state.state_label:
        badge_bg = (147, 51, 234, 230)     # Purple
    elif "FATIGUED" in state.state_label:
        badge_bg = (202, 138, 4, 220)      # Yellow-Brown
    else:
        badge_bg = (34, 197, 94, 230)      # Emerald Green

    # Format 24h clock string (e.g. 00:00 -> 08:30)
    hh = int(state.t_hours)
    mm = int((state.t_hours - hh) * 60)
    clock_str = f"T+{state.t_hours:04.1f}h  [{hh:02d}:{mm:02d}]"

    # Header Texts
    draw.text((16, 10), clock_str, fill=(255, 255, 255), font_size=17)
    from sim.drug_engine import get_chemical_name
    chem_display = get_chemical_name(drug_name)
    draw.text((170, 12), f"COMPOUND: {chem_display} (Dose: {dose:.1f})", fill=(203, 213, 225), font_size=14)

    # State Badge (Top Right)
    badge_w = 260
    badge_x = width - badge_w - 12
    draw.rounded_rectangle([badge_x, 8, width - 12, 44], radius=6, fill=badge_bg)
    draw.text((badge_x + 12, 14), state.state_label, fill=(255, 255, 255), font_size=13)

    # Bottom Telemetry Strip
    col1 = f"CONC: {state.plasma_conc*100:4.1f}%"
    col2 = f"SLEEP DEBT: {state.process_s*100:4.1f}%"
    col3 = f"FATIGUE: {state.perceived_fatigue*100:4.1f}%"
    col4 = f"SPEED: {state.walk_speed_m_s:4.2f} m/s"
    col5 = f"CADENCE: {state.cadence_hz:4.2f} Hz"

    y_bot = height - 30
    draw.text((16, y_bot), col1, fill=(56, 189, 248), font_size=13)
    draw.text((140, y_bot), col2, fill=(244, 114, 182), font_size=13)
    draw.text((290, y_bot), col3, fill=(250, 204, 21), font_size=13)
    draw.text((430, y_bot), col4, fill=(74, 222, 128), font_size=13)
    draw.text((540, y_bot), col5, fill=(226, 232, 240), font_size=13)

    # Progress bar along bottom
    prog_w = int((checkpoint_idx / max(1, total_checkpoints - 1)) * width)
    draw.rectangle([0, height - 4, prog_w, height], fill=(56, 189, 248, 255))

    return np.array(img)


# =====================================================================
# 4. Long-Term Timelapse Generation Pipeline
# =====================================================================

def generate_long_term_timelapse(
    drug_name: str = "Caffeine",
    dose: float = 1.0,
    total_hours: float = 24.0,
    checkpoints: list[float] | None = None,
    probe_duration: float = 0.8,
    fps: int = 20,
    out_path: str = "out/long_term_caffeine_timelapse.mp4",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generates a complete long-term chronobiological timelapse video and telemetry.
    
    Args:
        drug_name: Modeled compound (e.g., 'Caffeine', 'Dormiphen (Sleeping Pill)', 'Lidocaine').
        dose: Administered drug dose [0.0 - 1.0].
        total_hours: Total chronological time span to simulate (e.g., 12.0 or 24.0 hours).
        checkpoints: Explicit list of chronological hours to probe (defaults to hourly progression).
        probe_duration: Physical simulated seconds executed per hourly checkpoint.
        fps: Playback frame rate for the output video/GIF.
        out_path: Destination file path (.mp4 or .gif).

    Returns:
        Tuple of (summary_dict, timeseries_state_list).
    """
    import mujoco
    import imageio

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    engine = LongTermPKPDEngine(drug_name=drug_name, dose=dose)

    if checkpoints is None:
        # Canonical 24-hour arc: dense early sampling (absorption/peak) + steady progression
        if total_hours <= 12.0:
            checkpoints = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]
        else:
            checkpoints = [
                0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0,
                7.0, 8.0, 9.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0
            ]

    print(f"\n=================================================================")
    print(f"  HIGHFISH LONG-TERM PHARMACOLOGICAL TIMELAPSE: {drug_name.upper()}")
    print(f"=================================================================")
    print(f"  Chronological Timeline: 0.0h -> {total_hours:.1f}h ({len(checkpoints)} stroboscopic checkpoints)")
    print(f"  Pharmacokinetics: t1/2(elim) = {engine.profile.t_half_elim_h:.1f}h | t_max = {engine.profile.t_max_h:.2f}h")
    print(f"  Output Video: {out_path} ({fps} fps)")

    all_states: list[dict[str, Any]] = []
    video_frames: list[np.ndarray] = []

    # Initialize a shared pipeline simulator for embodied probes
    # (re-used across checkpoints to ensure instant speed and memory efficiency)
    sim = HumanPipelineSim(drug_name=drug_name, dose=dose, harness=True, harness_support=1.0)
    renderer = mujoco.Renderer(sim.body.mj_model, height=480, width=640)

    for idx, t_hr in enumerate(checkpoints):
        state = engine.compute_state(t_hr)
        all_states.append(asdict(state))

        # Dynamically inject the chronological physiological state into the humanoid translator & gait
        # 1) Scale Na_v excitability
        sim.neural.excitability_scale = state.para_scale
        # 2) Modulate sensory wake drive
        sim.neural.arousal_attenuation = float(np.clip(state.net_arousal_gain, 0.2, 1.5))
        # 3) Update drug sim parameters override
        sim.sim_params["d1_like_gain"] = float(0.20 * state.effective_effect)
        sim.sim_params["ort_histamine_phi"] = float(0.45 * state.effective_effect)
        if "Lidocaine" in drug_name:
            sim.sim_params["para_nav_phi"] = float(0.70 * state.effective_effect)

        # Run a brief embodied MuJoCo physics probe (probe_duration seconds)
        n_steps = int(probe_duration / 0.002)
        # Capture frames across the probe
        for step_i in range(n_steps):
            # Advance neural & biped physics
            if step_i % 10 == 0:
                sim.neural.step()
                intent = sim.translator.translate(sim.neural, sim.mod, sim.stim_mgr)
                # Apply chronobiological speed and tone adjustments
                intent.forward_drive = float(np.clip(intent.forward_drive * state.net_arousal_gain, 0.05, 1.0))
                intent.motor_tone = float(np.clip(intent.motor_tone * state.para_scale, 0.1, 1.0))
                intent.posture_height = state.posture_height
                intent.cadence = state.cadence_hz

            phi_l, phi_r = sim.cpg.step(0.002, intent)
            joint_targets = sim.kin.compute_joint_targets(0.002, phi_l, phi_r, intent)
            sim.body.step(joint_targets)

            # Record ~6 frames per checkpoint probe (e.g. step_i % 25 == 0)
            if step_i % 25 == 0:
                renderer.update_scene(sim.body.mj_data, camera="trackcam")
                raw_frame = renderer.render()
                hud_frame = draw_timelapse_hud(
                    raw_frame,
                    state,
                    drug_name,
                    dose,
                    checkpoint_idx=idx,
                    total_checkpoints=len(checkpoints),
                )
                video_frames.append(hud_frame)

        print(f"  [T+{state.t_hours:4.1f}h] Conc: {state.plasma_conc*100:4.1f}% | SleepDebt: {state.process_s*100:4.1f}% | "
              f"Fatigue: {state.perceived_fatigue*100:4.1f}% | Vx: {state.walk_speed_m_s:.2f} m/s | {state.state_label}")

    sim.close()

    # Save output video / GIF
    print(f"\nWriting {len(video_frames)} frames to {out_path}...")
    if out_path.lower().endswith(".gif"):
        imageio.mimsave(out_path, video_frames, fps=fps, loop=0)
    else:
        imageio.mimsave(out_path, video_frames, fps=fps)

    summary = {
        "drug_name": drug_name,
        "dose": dose,
        "total_hours": total_hours,
        "checkpoints_count": len(checkpoints),
        "video_path": out_path,
        "video_duration_s": round(len(video_frames) / fps, 2),
        "frames_rendered": len(video_frames),
        "pk_profile": asdict(engine.profile),
        "key_phases": {
            "peak_concentration_h": engine.profile.t_max_h,
            "elimination_t_half_h": engine.profile.t_half_elim_h,
            "max_speed_m_s": max(s["walk_speed_m_s"] for s in all_states),
            "min_speed_m_s": min(s["walk_speed_m_s"] for s in all_states),
            "final_speed_m_s": all_states[-1]["walk_speed_m_s"],
        },
    }

    # Save telemetry JSON alongside output
    json_path = str(Path(out_path).with_suffix(".json"))
    with open(json_path, "w") as f:
        json.dump({"summary": summary, "timeline": all_states}, f, indent=2)
    print(f"Telemetry saved to {json_path}")
    print(f"Long-term timelapse complete!")

    return summary, all_states


if __name__ == "__main__":
    generate_long_term_timelapse(
        drug_name="Caffeine",
        dose=1.0,
        total_hours=24.0,
        out_path="out/long_term_caffeine_24h.mp4",
    )
