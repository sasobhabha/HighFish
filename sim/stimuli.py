#!/usr/bin/env python3
"""Environment stimuli: food and predators for reaction-time assays.

Scientific basis (citations.md):
- Looming (approaching) visual stimuli trigger escape in larval zebrafish via
  loom-sensitive retinal/tectal circuits and hindbrain (reticulospinal-like)
  descending pathways [C182, C183]. Larvae freeze or flee depending on stimulus
  parameters [C184, C185].
- Food odor / prey drive approach via attraction circuits (modeled here as weak
  positive drive + steering toward the food source; simplification - the
  biological attractant circuitry is olfactory bulb -> telencephalon/tectum).

This module owns the stimulus OBJECTS (mocap bodies rendered in the MuJoCo
scene), their kinematics, the per-step stimulus intensity signal fed to the
neural sim, and the reaction-time recorder.
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Stimulus:
    kind: str                 # "food" | "predator"
    name: str                 # mocap body name
    pos: np.ndarray           # world xy(z), mm
    speed: float = 0.0        # mm/s movement toward the animal (predator)
    radius: float = 0.4       # visual size (mm)
    active: bool = False      # becomes active at trigger time
    onset_t: float | None = None
    responded: bool = False
    response_t: float | None = None
    reached: bool = False     # food consumed / predator contacted


@dataclass
class StimulusConfig:
    food: bool = False
    predator: bool = False
    predator_speed: float = 1.6      # m/s approach (looming chase; biped walks
                                     # ~1.15 m/s, so the disc slowly closes in)
    food_gain: float = 0.45          # attraction drive strength
    predator_gain: float = 2.2       # looming -> escape drive strength
    freeze_flee_threshold: float = 0.55  # min DN-drive for flee vs freeze [C185]
    min_sensory_latency: float = 0.060   # retinal/tectal + hindbrain transmission
                                         # floor before motor drive can rise (s)


class StimulusManager:
    """Owns stimuli, moves them, and computes neural stimulus intensity."""

    def __init__(self, cfg: StimulusConfig):
        self.cfg = cfg
        self.stimuli: list[Stimulus] = []
        self.pending: list[tuple[float, str]] = []   # (t_onset, kind) sorted
        self.history: list[dict] = []
        self._baseline_drive: float | None = None    # pre-stimulus DN drive EMA
        self._fwd_ema: np.ndarray | None = None      # smoothed heading (see update)
        self.feeding = False   # True once the animal reaches food; gates locomotion

    # ---------- setup ----------
    def schedule(self, t_onset: float, kind: str):
        self.pending.append((t_onset, kind))
        self.pending.sort()

    def _spawn(self, kind: str, animal_pos: np.ndarray) -> Stimulus:
        # Positions are in METERS (matching the MuJoCo biped world): the legacy
        # prototype spawn distances (mm) made the looming intensity
        # speed/dist collapse within one neural step of onset.
        if kind == "food":
            # food item ~2 m ahead-right of the animal, on the floor
            pos = animal_pos + np.array([2.0, 1.2, 0.0])
            pos[2] = 0.15
            s = Stimulus(kind="food", name="food_stim", pos=pos, radius=0.3)
        else:
            # looming disc starts ~2.2 m ahead of the animal at chest height
            pos = animal_pos + np.array([2.2, -1.2, 0.0])
            pos[2] = 0.9
            s = Stimulus(kind="predator", name="predator_stim", pos=pos,
                         speed=self.cfg.predator_speed, radius=0.35)
        self.stimuli.append(s)
        return s

    def mocap_bodies(self) -> list[dict]:
        """Mocap bodies to create in the world.

        The food stimulus is a food item (yellow elongated pellet); the predator
        is a dark looming disc (cited looming-escape stimulus, C182-C185).
        """
        return [
            {"name": "food_stim", "kind": "food_pellet",
             "pos": [2.0, 1.2, 0.15], "size": [0.3, 0.12],
             "rgba": [0.95, 0.85, 0.15, 1.0], "tip_rgba": [0.45, 0.28, 0.08, 1.0]},
            {"name": "predator_stim", "kind": "disc",
             "pos": [-50.0, -50.0, 0.9], "size": [0.35],
             "rgba": [0.55, 0.05, 0.02, 0.99]},
        ]

    # ---------- per-step update ----------
    def update(self, t: float, animal_pos: np.ndarray, animal_forward: np.ndarray,
               dn_drive: float, dt: float = 1e-3) -> dict:
        """Activate/move stimuli; returns per-step stimulus signals + events."""
        # activation
        while self.pending and t >= self.pending[0][0]:
            _, kind = self.pending.pop(0)
            s = self._spawn(kind, animal_pos)
            s.active = True
            s.onset_t = t
            self.history.append({"event": f"{kind}_onset", "t": t})

        signals = {"food_gain": 0.0, "predator_intensity": 0.0}
        events = []
        # Smoothed heading (EMA, ~0.5 s time constant at 1 kHz updates): the gait
        # yaw-waddles +-25 deg at stepping frequency, so steering computed from
        # the INSTANTANEOUS forward vector flips sign every step, slamming the
        # left/right stroke-amplitude asymmetry and flipping the animal at food
        # onset (observed: flip 0.2 s after food spawn). Smoothing averages the
        # wobble out and yields the true mean heading.
        fwd_xy = np.asarray(animal_forward[:2], dtype=float)
        if self._fwd_ema is None:
            self._fwd_ema = fwd_xy.copy()
        else:
            self._fwd_ema = 0.998 * self._fwd_ema + 0.002 * fwd_xy
        # baseline DN drive (EMA) used for response detection; frozen while a
        # predator is active so latencies are measured against pre-stimulus level
        preds_active = any(s.kind == "predator" and s.active
                           for s in self.stimuli)
        if not preds_active:
            self._baseline_drive = (0.9 * self._baseline_drive + 0.1 * dn_drive
                                    if self._baseline_drive is not None else dn_drive)
        for s in self.stimuli:
            if not s.active:
                continue
            vec = animal_pos[:2] - s.pos[:2]
            dist = float(np.linalg.norm(vec))
            if s.kind == "food":
                # attraction grows as food gets closer (odor plume proxy)
                proximity = 1.0 / (1.0 + dist / 0.8)
                signals["food_gain"] = self.cfg.food_gain * proximity
                # steering toward food: signed angle between SMOOTHED forward
                # and food dir; capped at 1.0 ((1-dot) reaches 2 when facing
                # away, and an uncapped command saturates the bridge's side
                # amplitude asymmetry -> violent lurch)
                food_dir = vec / max(dist, 1e-6)
                fwd_s = self._fwd_ema / max(np.linalg.norm(self._fwd_ema), 1e-6)
                cross = fwd_s[0] * food_dir[1] - fwd_s[1] * food_dir[0]
                dot = float(np.clip(np.dot(fwd_s, food_dir), -1, 1))
                signals["turn_bias"] = float(np.clip(np.sign(cross) * (1.0 - dot),
                                                     -1.0, 1.0))
                # reach radius 0.5 m > pellet half-length (0.3 m): a plain
                # center-distance check can miss end-on approaches
                if dist < 0.5 and not s.reached:
                    s.reached = True
                    self.feeding = True   # animal stops to feed (locomotion gate)
                    events.append({"event": "food_reached", "t": t,
                                   "latency": t - (s.onset_t or t)})
                    self.history.append(events[-1])
            else:  # predator
                # looming: intensity ~ approach speed / distance (time-to-contact)
                intensity = float(min(2.0, s.speed / max(dist, 0.5)))
                signals["predator_intensity"] = intensity
                # escape overrides feeding: a looming predator interrupts the meal
                if intensity > 0.5 and self.feeding:
                    self.feeding = False
                    self.history.append({"event": "feeding_interrupted", "t": t})
                # move toward the animal
                if dist > 0.6:
                    s.pos[:2] += vec / max(dist, 1e-6) * s.speed * dt
                # contact
                if dist < 0.6 and not s.responded:
                    s.responded = True
                    events.append({"event": "predator_contact", "t": t,
                                   "latency": None})
                    self.history.append(events[-1])
        # reaction time: did the animal respond to an active looming stimulus?
        if signals["predator_intensity"] > 0 and not self._resp_check_done():
            self._check_response(t, dn_drive, self._baseline_drive or 0.5)
        signals["events"] = events
        signals["feeding"] = self.feeding
        return signals

    def _resp_check_done(self) -> bool:
        preds = [s for s in self.stimuli if s.kind == "predator" and s.active]
        return not preds or all(s.responded for s in preds)

    def _check_response(self, t: float, dn_drive: float, baseline: float):
        """Response detection relative to pre-stimulus baseline drive:
        flee = drive rises >=12% above baseline AND exceeds an absolute
        behavioral threshold (0.45; below it the animal cannot sustain an
        escape run - e.g. under strong Nav block it freezes instead);
        freeze = neither within 1 s of onset [C185: flies freeze or flee]."""
        for s in self.stimuli:
            if (s.kind == "predator" and s.active and not s.responded
                    and s.onset_t is not None):
                # no response before the sensory-processing floor: visual loom
                # signals take tens of ms to reach hindbrain motor drive
                if t - s.onset_t < self.cfg.min_sensory_latency:
                    continue
                flee_threshold = max(1.12 * baseline + 0.02, 0.45)
                if dn_drive >= flee_threshold:
                    s.responded = True
                    s.response_t = t
                    rec = {"event": "escape_response", "t": t,
                           "latency": t - s.onset_t, "mode": "flee",
                           "baseline": round(baseline, 3),
                           "drive": round(dn_drive, 3)}
                    self.history.append(rec)
                elif t - s.onset_t > 1.0 and dn_drive < 0.7 * baseline:
                    s.responded = True
                    s.response_t = t
                    rec = {"event": "escape_response", "t": t,
                           "latency": None, "mode": "freeze",
                           "baseline": round(baseline, 3),
                           "drive": round(dn_drive, 3)}
                    self.history.append(rec)

    def reaction_times(self) -> list[dict]:
        return [h for h in self.history if h["event"] == "escape_response"]

    def mocap_positions(self) -> dict[str, np.ndarray]:
        out = {}
        for s in self.stimuli:
            if s.active:
                out[s.name] = s.pos
        return out
