#!/usr/bin/env python3
"""End-to-end human locomotion pipeline.

Wires:
  FlyWire v783 connectome (FlyWireNeuralSim)
    ↓ (descending neuron population rates)
  Neuro-Human Translation Layer (DNToHumanTranslator -> HumanIntent)
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
from sim.human_translation import DNToHumanTranslator, HumanIntent
from sim.humanoid_body import HumanoidBodySim
from sim.neural_sim import FlyWireNeuralSim
from sim.stimuli import StimulusConfig, StimulusManager

NEURAL_DT = 0.002       # Neural integration step (s)
PHYSICS_DT = 0.002      # MuJoCo physics integration step (s)


class HumanPipelineSim:
    """Integrated simulation pipeline coupling FlyWire neural dynamics to a humanoid biped."""

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

        # 2. FlyWire Connectome Rate Network
        self.neural = FlyWireNeuralSim()
        if self.mod.get("fly_mapping"):
            self.neural.apply_drug(self.mod["fly_mapping"], self.sim_params)

        # 3. Translation Layer
        self.translator = DNToHumanTranslator()

        # 4. Biped CPG & Kinematics
        self.cpg = BipedCPG(seed=seed)
        self.kin = BipedGaitKinematics()

        # 5. MuJoCo Humanoid Body Simulation
        self.body = HumanoidBodySim(
            harness=harness,
            harness_support=harness_support,
            dt=PHYSICS_DT,
        )

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
        t_wall_start = time.time()
        intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)

        for step_idx in range(n_steps):
            t_sim = step_idx * PHYSICS_DT

            # 1. Update stimulus drives based on humanoid position
            curr_pos = self.body.mj_data.xpos[self.body.pelvis_id]
            pos_mm = np.array([curr_pos[0] * 1000.0, curr_pos[1] * 1000.0, curr_pos[2] * 1000.0])
            fwd_vec = np.array([1.0, 0.0, 0.0])

            stim_signals = self.stim_mgr.update(
                t=t_sim,
                fly_pos=pos_mm,
                fly_forward=fwd_vec,
                dn_drive=self.last_drive,
            )
            self.neural.apply_stim(
                food_gain=stim_signals.get("food_gain", 0.0),
                predator_intensity=stim_signals.get("predator_intensity", 0.0),
                turn_bias=stim_signals.get("turn_bias", 0.0),
            )

            # 3. Step FlyWire rate network at 50 Hz (every 10 physics steps, tau_r = 20ms)
            if step_idx % 10 == 0:
                self.neural.step()
                r_dn = float(np.mean(self.neural.r[self.translator.all_dn_idx]))
                p_int = float(stim_signals.get("predator_intensity", 0.0))
                if p_int > 0:
                    self.last_drive = min(2.0, r_dn + 0.6 * p_int)
                else:
                    self.last_drive = r_dn

                # 4. Translate descending readout -> HumanIntent
                intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)

            # 5. Advance Biped CPG & Kinematics (at PHYSICS_DT = 0.002s)
            phi_l, phi_r = self.cpg.step(PHYSICS_DT, intent)
            joint_targets = self.kin.compute_joint_targets(PHYSICS_DT, phi_l, phi_r, intent)

            # 6. Advance MuJoCo Physics
            self.body.harness_support = self.harness_support * float(np.clip(intent.posture_height, 0.2, 1.0))
            state = self.body.step(joint_targets)

            # 7. Update live viewer at 60 Hz with wall-clock sync scaled by timelapse factor
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
            "outcome": "fallen" if body_metrics["fall_detected"] else "completed",
            "body_metrics": body_metrics,
            "intent_summary": intent_summary,
            "mean_sync_error": mean_sync_err,
            "reaction_times": self.stim_mgr.reaction_times(),
            "stimulus_events": self.stim_mgr.history,
            "pharmacology": {
                "fly_mapping": self.mod.get("fly_mapping", {}),
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
        intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)
        for step_idx in range(n_steps):
            t_sim = step_idx * PHYSICS_DT
            curr_pos = self.body.mj_data.xpos[self.body.pelvis_id]
            pos_mm = np.array([curr_pos[0] * 1000.0, curr_pos[1] * 1000.0, 0.0])
            fwd_vec = np.array([1.0, 0.0, 0.0])

            stim_signals = self.stim_mgr.update(
                t=t_sim,
                fly_pos=pos_mm,
                fly_forward=fwd_vec,
                dn_drive=self.last_drive,
            )
            self.neural.apply_stim(
                food_gain=stim_signals.get("food_gain", 0.0),
                predator_intensity=stim_signals.get("predator_intensity", 0.0),
                turn_bias=stim_signals.get("turn_bias", 0.0),
            )
            if step_idx % 10 == 0:
                self.neural.step()
                r_dn = float(np.mean(self.neural.r[self.translator.all_dn_idx]))
                p_int = float(stim_signals.get("predator_intensity", 0.0))
                if p_int > 0:
                    self.last_drive = min(2.0, r_dn + 0.6 * p_int)
                else:
                    self.last_drive = r_dn
                intent = self.translator.translate(self.neural, self.mod, self.stim_mgr)
            phi_l, phi_r = self.cpg.step(PHYSICS_DT, intent)
            joint_targets = self.kin.compute_joint_targets(PHYSICS_DT, phi_l, phi_r, intent)

            self.body.harness_support = self.harness_support * float(np.clip(intent.posture_height, 0.2, 1.0))
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
