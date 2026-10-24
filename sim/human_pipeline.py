#!/usr/bin/env python3
"""End-to-end human locomotion pipeline.

Wires:
  Zebrafish (Fish1) connectome (ZebrafishNeuralSim)
    ↓ (hindbrain reticulospinal-like readout rates)
  Direct Motor Readout (ZebrafishReadout -> HumanIntent)
    ↓ (cadence, stride, coordination, motor tone)
  Biped Central Pattern Generator & Limb Kinematics (BipedCPG + BipedGaitKinematics)
    ↓ (joint angle target trajectories)
  Embodied Humanoid Scaffold (HumanoidBodySim / MuJoCo physics)
    ↓
  Biomechanical & Clinical Metrics (Vx, straightness, step symmetry, biped coordination)
"""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.drug_engine import drug_modulation
from sim.human_gait import BipedCPG, BipedGaitKinematics
from sim.fish_readout import ZebrafishReadout, HumanIntent
from sim.humanoid_body import HumanoidBodySim
from sim.neural_sim import ZebrafishNeuralSim
from sim.stimuli import StimulusConfig, StimulusManager

# ---------------------------------------------------------------------------
NEURAL_DT = 0.002       # Neural integration step (s)
PHYSICS_DT = 0.002      # MuJoCo physics integration step (s)

# Limp-on-collapse dwell: pelvis must stay below the fall threshold this long
# (no recovery) before the motors are cut and gravity finishes the fall.
FALL_DWELL_S = 0.3

# Vestibulospinal balance-authority mapping: closed-loop balance assist scales
# with motor tone x posture (erectness). Healthy walk -> full balance;
# drug-crushed tone/posture -> weak balance -> real topple + fall.
BALANCE_BASE = 0.15
BALANCE_GAIN_SCALE = 0.85


class HumanPipelineSim:
    """Integrated simulation pipeline coupling zebrafish-connectome neural dynamics to a humanoid biped."""

    def __init__(
        self,
        drug_name: str | None = None,
        dose: float = 1.0,
        seed: int = 0,
        harness: bool = True,
        harness_support: float = 1.0,
        stim_cfg: StimulusConfig | None = None,
        sim_params_override: dict[str, Any] | None = None,
    ):
        self.drug_name = drug_name
        self.dose = dose
        self.harness_support = harness_support
        self.stim_cfg = stim_cfg or StimulusConfig()
        self.stim_mgr = StimulusManager(self.stim_cfg)

        # 1. Pharmacology & receptor modulation
        self.mod = drug_modulation(drug_name, dose)
        self.sim_params = dict(self.mod.get("sim_params", {}))
        if sim_params_override:
            self.sim_params.update(sim_params_override)
            self.mod["sim_params"] = self.sim_params

        # 2. Zebrafish Connectome Rate Network
        self.neural = ZebrafishNeuralSim()
        if self.mod.get("fish_mapping"):
            self.neural.apply_drug(self.mod["fish_mapping"], self.sim_params)
        elif sim_params_override:
            # sim_params-only override (e.g. the GABA_A-block assay run with
            # drug_name=None): derive receptor-blocker mapping from the *_phi
            # occupancy keys so the network actually receives the block.
            _L = "_phi"
            mapping = {}
            for key in sim_params_override:
                system = key[:-len(_L)] if key.endswith(_L) else None
                if system == "rdl":            # legacy Drosophila-era name
                    system = "gaba_a"
                if system:
                    mapping[system] = {"direction": "antagonist"}
            if mapping:
                self.neural.apply_drug(mapping, self.sim_params)

        # 3. Direct Motor Readout (hindbrain readout -> intent)
        self.translator = ZebrafishReadout()
        self.translator.all_dn_idx = self.neural.readout_idx

        # 4. Biped CPG & Kinematics
        self.cpg = BipedCPG(seed=seed)
        self.kin = BipedGaitKinematics()

        # 5. MuJoCo Humanoid Body Simulation
        self.body = HumanoidBodySim(
            harness=harness,
            harness_support=harness_support,
            dt=PHYSICS_DT,
        )

        # Freejoint walking needs softly-damped leg servos (gait-critical);
        # the harness model keeps its original tuning untouched.
        if not harness:
            for _joint, _kp in (("knee", 500.0), ("hip_pitch", 600.0), ("ankle", 60.0)):
                _aid = self.body.act_map.get(f"act_left_{_joint}")
                if _aid is None:
                    continue
                for _pre in ("left_", "right_"):
                    _aid = self.body.act_map[f"act_{_pre}{_joint}"]
                    self.body.mj_model.actuator_biasprm[_aid, 2] = -(_kp * 0.03)
            # Gait initiation: real biped gait must ramp in, or t=0 full CPG
            # amplitude kicks the freed body off balance instantly. The full
            # stride intent (clip 1.4) also overswings an unassisted biped,
            # so freejoint mode walks on a moderated stride.
            self.kin.start_ramp = 0.6
            self.kin.stride_scale = 0.65
            self.kin.max_slew = 8.0

        safe_name = "".join(c if c.isalnum() else "_" for c in (drug_name or "vehicle"))[:30]
        self.trial_id = f"human_trial_{int(time.time())}_{safe_name}"
        self.last_drive = 0.5

    def run(
        self,
        duration: float = 3.0,
        viewer: Any = None,
        stim_schedule: list[tuple[float, str]] | None = None,
        terminate_on: str = "none",
        timelapse: float = 1.0,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Runs the coupled neuro-biomechanical simulation for the specified duration.

        Args:
            duration: Simulated duration in seconds.
            viewer: Optional active MuJoCo passive viewer.
            stim_schedule: Optional list of (time_s, event_name) stimulus triggers.
            terminate_on: Early exit condition ("any", "fall", "none").

        Returns:
            Tuple of (metrics_dict, timeseries_log_dict).
        """
        # Schedule any external stimulus events
        schedule = sorted(stim_schedule or [], key=lambda x: x[0])
        for t_onset, kind in schedule:
            self.stim_mgr.schedule(t_onset, kind)

        n_steps = int(np.ceil(duration / PHYSICS_DT))

        # Time-series log
        log: dict[str, list[Any]] = {
            "t": [],
            "intent": [],
            "pos": [],
            "sync_error": [],
        }

        # Initialize neural warmup
        for _ in range(40):
            self.neural.step()

        t_sim = 0.0
        terminated = None
        fall_time_s = None
        state = None
        fall_window_start = None   # dwell timer: sustained buckle = real fall
        t_wall_start = time.time()
        intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)

        for step_idx in range(n_steps):
            t_sim = step_idx * PHYSICS_DT

            # 1. Update stimulus drives based on humanoid position
            curr_pos = self.body.mj_data.xpos[self.body.pelvis_id]
            pos = np.array(curr_pos, dtype=float)  # meters (stimulus scale)
            fwd_vec = np.array([1.0, 0.0, 0.0])

            stim_signals = self.stim_mgr.update(
                t=t_sim,
                animal_pos=pos,
                animal_forward=fwd_vec,
                dn_drive=self.last_drive,
                dt=PHYSICS_DT,
            )
            self.neural.apply_stim(
                food_gain=stim_signals.get("food_gain", 0.0),
                predator_intensity=stim_signals.get("predator_intensity", 0.0),
                turn_bias=stim_signals.get("turn_bias", 0.0),
            )

            # 3. Step zebrafish rate network at 50 Hz (every 10 physics steps, tau_r = 20ms)
            if step_idx % 10 == 0:
                self.neural.step()
                r_dn = self.neural.readout_output()
                p_int = float(stim_signals.get("predator_intensity", 0.0))
                if p_int > 0:
                    self.last_drive = min(2.0, r_dn + 0.6 * p_int)
                else:
                    self.last_drive = r_dn

                # 4. Translate hindbrain readout -> HumanIntent
                intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)

            # 5. Advance Biped CPG & Kinematics (at PHYSICS_DT = 0.002s)
            phi_l, phi_r = self.cpg.step(PHYSICS_DT, intent)
            joint_targets = self.kin.compute_joint_targets(PHYSICS_DT, phi_l, phi_r, intent)

            # 6. Advance MuJoCo Physics
            # Limp-on-collapse: if the pelvis stays below the fall threshold
            # for FALL_DWELL_S without recovering, the knees have buckled for
            # good -- cut motor drive so gravity finishes the fall (no ghost
            # sitting with buckled knees held by servos). Brief bounces that
            # recover are tolerated.
            if (not self.body.actuators_released and state is not None
                    and self.body.step_count > 0):
                if state["z"] < 0.45:
                    if fall_window_start is None:
                        fall_window_start = t_sim
                    elif t_sim - fall_window_start >= FALL_DWELL_S:
                        self.body.release_actuators()
                        fall_time_s = fall_window_start
                else:
                    fall_window_start = None

            # Vestibulospinal balance authority: tone x erectness x reciprocal
            # coordination, low-pass filtered so brief neural wobbles don't kill
            # balance (real balance reactions average over tens of ms).
            bal_raw = BALANCE_BASE + BALANCE_GAIN_SCALE * float(np.clip(
                intent.motor_tone * intent.posture_height * intent.coordination, 0.0, 1.0))
            self.body.balance_gain = (0.90 * self.body.balance_gain + 0.10 * bal_raw)
            state = self.body.step(joint_targets)
            if viewer is not None and step_idx % 8 == 0:
                if not viewer.is_running():
                    break
                viewer.sync()
                if timelapse > 0:
                    wall_elapsed = time.time() - t_wall_start
                    target_wall = t_sim / timelapse
                    if wall_elapsed < target_wall:
                        time.sleep(min(0.016, target_wall - wall_elapsed))

            # 8. Record telemetry at ~50 Hz (every 10 steps)
            if step_idx % 10 == 0:
                log["t"].append(t_sim)
                log["intent"].append(asdict(intent))
                log["pos"].append([state["x"], state["y"], state["z"]])
                log["sync_error"].append(self.cpg.phase_sync_error())

            # 9. Termination checks
            if terminate_on in ("any", "fall") and state["z"] < 0.45:
                terminated = "fall"
                break

        # Compile comprehensive metrics
        body_metrics = self.body.get_metrics()
        intents = log["intent"]

        intent_summary = {}
        if intents:
            for k in ("forward_drive", "cadence", "stride_length", "posture_height",
                      "coordination", "motor_tone", "turn_intent"):
                vals = [entry[k] for entry in intents]
                intent_summary[f"mean_{k}"] = round(float(np.mean(vals)), 4)
            intent_summary["final_mode"] = intents[-1]["mode"]

        sync_errors = log["sync_error"]
        mean_sync_err = round(float(np.mean(sync_errors)), 4) if sync_errors else 0.0

        metrics = {
            "trial_id": self.trial_id,
            "drug_name": self.drug_name,
            "dose": self.dose,
            "duration_s": round(t_sim, 3),
            "terminated": terminated,
            "fall_time_s": fall_time_s,
            "outcome": "fallen" if body_metrics["fall_detected"] else "completed",
            "body_metrics": body_metrics,
            "intent_summary": intent_summary,
            "mean_sync_error": mean_sync_err,
            "reaction_times": self.stim_mgr.reaction_times(),
            "stimulus_events": self.stim_mgr.history,
            "pharmacology": {
                "fish_mapping": self.mod.get("fish_mapping", {}),
                "sim_params": self.sim_params,
            },
        }

        return metrics, log

    def render_video(
        self,
        out_path: str,
        duration: float = 3.0,
        fps: int = 30,
        camera: str = "trackcam",
        stim_schedule: list[tuple[float, str]] | None = None,
        timelapse: float = 1.0,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Renders 3D humanoid locomotion to an MP4 or GIF video file.
        
        Args:
            out_path: Path to destination file (.mp4 or .gif).
            duration: Total simulated physical duration in seconds.
            fps: Frame rate of the generated output video.
            camera: Camera name ('trackcam' or None for default).
            stim_schedule: Optional list of (time_s, event_name).
            timelapse: Speedup multiplier (e.g. 1.0 = real-time, 5.0 = 5x faster timelapse).
        """
        import mujoco
        import imageio
        from pathlib import Path

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        schedule = sorted(stim_schedule or [], key=lambda x: x[0])
        for t_onset, kind in schedule:
            self.stim_mgr.schedule(t_onset, kind)

        n_steps = int(np.ceil(duration / PHYSICS_DT))
        # Adjust interval so 1 second of video displays (fps * interval * dt) seconds of simulation.
        # timelapse=1.0 -> 1s video = 1s sim; timelapse=5.0 -> 1s video = 5s sim.
        render_interval = max(1, int(round(max(0.1, timelapse) / (fps * PHYSICS_DT))))
        renderer = mujoco.Renderer(self.body.mj_model, height=480, width=640)
        frames = []

        log: dict[str, list[Any]] = {
            "t": [],
            "intent": [],
            "pos": [],
            "sync_error": [],
        }

        for _ in range(40):
            self.neural.step()

        t_sim = 0.0
        state = None
        intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)
        for step_idx in range(n_steps):
            t_sim = step_idx * PHYSICS_DT
            curr_pos = self.body.mj_data.xpos[self.body.pelvis_id]
            pos = np.array([curr_pos[0], curr_pos[1], 0.0])  # meters (stimulus scale)
            fwd_vec = np.array([1.0, 0.0, 0.0])

            stim_signals = self.stim_mgr.update(
                t=t_sim,
                animal_pos=pos,
                animal_forward=fwd_vec,
                dn_drive=self.last_drive,
                dt=PHYSICS_DT,
            )
            self.neural.apply_stim(
                food_gain=stim_signals.get("food_gain", 0.0),
                predator_intensity=stim_signals.get("predator_intensity", 0.0),
                turn_bias=stim_signals.get("turn_bias", 0.0),
            )
            if step_idx % 10 == 0:
                self.neural.step()
                r_dn = self.neural.readout_output()
                p_int = float(stim_signals.get("predator_intensity", 0.0))
                if p_int > 0:
                    self.last_drive = min(2.0, r_dn + 0.6 * p_int)
                else:
                    self.last_drive = r_dn
                intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)
            phi_l, phi_r = self.cpg.step(PHYSICS_DT, intent)
            joint_targets = self.kin.compute_joint_targets(PHYSICS_DT, phi_l, phi_r, intent)

            # Advance MuJoCo physics (same limp-on-collapse as run())
            if (not self.body.actuators_released
                    and self.body.step_count > 0
                    and state is not None and state["z"] < 0.45):
                self.body.release_actuators()
            # Vestibulospinal balance authority (same smoothing as run())
            bal_raw = BALANCE_BASE + BALANCE_GAIN_SCALE * float(np.clip(
                intent.motor_tone * intent.posture_height * intent.coordination, 0.0, 1.0))
            self.body.balance_gain = (0.90 * self.body.balance_gain + 0.10 * bal_raw)
            state = self.body.step(joint_targets)

            if step_idx % render_interval == 0:
                renderer.update_scene(self.body.mj_data, camera=camera)
                frames.append(renderer.render())

            if step_idx % 10 == 0:
                log["t"].append(t_sim)
                log["intent"].append(asdict(intent))
                log["pos"].append([state["x"], state["y"], state["z"]])
                log["sync_error"].append(self.cpg.phase_sync_error())

        if out_path.lower().endswith(".gif"):
            imageio.mimsave(out_path, frames, fps=fps, loop=0)
        else:
            imageio.mimsave(out_path, frames, fps=fps)

        body_metrics = self.body.get_metrics()
        intents = log["intent"]
        intent_summary = {}
        if intents:
            for k in ("forward_drive", "cadence", "stride_length", "posture_height",
                      "coordination", "motor_tone", "turn_intent"):
                vals = [entry[k] for entry in intents]
                intent_summary[f"mean_{k}"] = round(float(np.mean(vals)), 4)
            intent_summary["final_mode"] = intents[-1]["mode"]

        sync_errors = log["sync_error"]
        mean_sync_err = round(float(np.mean(sync_errors)), 4) if sync_errors else 0.0

        metrics = {
            "trial_id": self.trial_id,
            "drug_name": self.drug_name,
            "dose": self.dose,
            "duration_s": round(t_sim, 3),
            "timelapse_factor": float(timelapse),
            "video_duration_s": round(len(frames) / max(1, fps), 2),
            "video_path": out_path,
            "frames_rendered": len(frames),
            "outcome": "fallen" if body_metrics["fall_detected"] else "completed",
            "body_metrics": body_metrics,
            "intent_summary": intent_summary,
            "mean_sync_error": mean_sync_err,
            "reaction_times": self.stim_mgr.reaction_times(),
            "stimulus_events": self.stim_mgr.history,
        }
        return metrics, log

    def close(self):
        self.body.close()


if __name__ == "__main__":
    print("Testing HumanPipelineSim with baseline Vehicle...")
    pipeline = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    metrics, _ = pipeline.run(duration=2.0)
    pipeline.close()

    print("\nVehicle Simulation Metrics:")
    print(json.dumps(metrics, indent=2))
