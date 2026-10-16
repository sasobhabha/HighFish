#!/usr/bin/env python3
"""Embodied simulation: FlyWire brain rates -> CPG -> NeuroMechFly v2 body.

Usage:
    from sim.body_sim import DrugBodySim
    sim = DrugBodySim(drug_name="Caffeine")
    metrics, log = sim.run(duration=3.0, render=False)
"""
import json
import time
from pathlib import Path

import numpy as np

from sim.neural_sim import FlyWireNeuralSim, load_dn_indices
from sim.motor_bridge import LegCPG, MotorBridge, LEGS, TRIPOD1, TRIPOD2
from sim.drug_engine import drug_modulation
from sim.stimuli import StimulusConfig, StimulusManager

NEURAL_DT = 1e-3          # neural step (s)
PHYSICS_DT = 1e-4         # PDF Table 1
STEPS_PER_NEURAL = int(NEURAL_DT / PHYSICS_DT)
SUPINE_DEATH_S = 10.0     # flipped and unable to right within 10 s = death


class DrugBodySim:
    def __init__(self, drug_name: str | None = None, dose: float = 1.0,
                 seed: int = 0, headless_ok: bool = True, track_cam: bool = False,
                 stim_cfg: StimulusConfig | None = None):
        self.stim_mgr = StimulusManager(stim_cfg or StimulusConfig())
        self.drug_name = drug_name
        self.mod = drug_modulation(drug_name, dose)
        self.neural = FlyWireNeuralSim()
        self.dn = load_dn_indices()
        # apply drug to brain network
        self.neural.apply_drug(self.mod["fly_mapping"], self.mod["sim_params"])
        # para excitability scale feeds the CPG too
        self.para_scale = float(self.neural.excitability_scale)
        # VNC drug parameters: H1 (GABA/Rdl block) attenuates inter-leg coupling
        # (PDF Eq. 5). NOTE: ort_histamine does NOT belong here - HisCl1/Ort are
        # HISTAMINE-gated channels, not GABA receptors; blocking them must not
        # touch GABAergic synapses. Their wake-promoting role is modeled in the
        # brain net as arousal_attenuation (Oh 2013, C144).
        self.phi_gaba = float(self.mod["sim_params"].get("rdl_phi", 0.0))
        self.phi_gaba = min(1.0, self.phi_gaba)
        self.cpg = LegCPG(nu_base=7.0)
        # Arousal gating of the CPG drive from RECEPTOR-LEVEL parameters only:
        # (a) D1-like/DA gains are the fly wake/arousal pathway (caffeine acts
        # via DA signaling, C179/C180); (b) the histamine-HisCl1 axis is the
        # second wake pathway - blocking it attenuates the same gate (Oh 2013,
        # C144; this is what makes antihistamines drowsy). This is NOT a per-drug
        # outcome knob - both factors come from the drug's receptor mapping in
        # pharmacology.yaml, and behavior EMERGES from network dynamics.
        sp = self.mod["sim_params"]
        self.cpg_drive_gain = 1.0 \
            + float(sp.get("d1_like_gain", 0.0)) \
            + float(sp.get("da_gain", 0.0))
        self.cpg_drive_gain = float(np.clip(self.cpg_drive_gain, 0.5, 1.5)) \
            * float(self.neural.arousal_attenuation)
        # trial outcome machinery: death = supine >= SUPINE_DEATH_S;
        # survived = reached food (when terminate_on requests that outcome)
        self.terminated = None      # None | "survived" | "death"
        safe = "".join(c if c.isalnum() else "_" for c in (drug_name or "vehicle"))[:40]
        self.trial_id = f"trial_{int(time.time())}_{safe}"
        self._init_body(seed, track_cam=track_cam)

    def _init_body(self, seed, track_cam: bool = False):
        from flygym import Simulation
        from flygym.anatomy import ActuatedDOFPreset, AxisOrder, JointPreset, Skeleton
        from flygym.compose import (
            ActuatorType, FlatGroundWorld, KinematicPosePreset, NeuroMechFly,
        )
        from flygym.utils.math import Rotation3D

        self.fly = NeuroMechFly(name="nmf")
        # tracking close-up camera ALWAYS present (compiled name 'nmf/trackcam'):
        # a 1-mm fly on a 2-m ground plane is invisible to the default free camera
        self.fly.add_tracking_camera(name="trackcam")
        self.track_cam_name = "nmf/trackcam"
        self.skeleton = Skeleton(axis_order=AxisOrder.DONTCARE,
                                 joint_preset=JointPreset.LEGS_ACTIVE_ONLY)
        # Soften passive springs (default stiffness=10, damping=0.5): with a
        # strong position servo the stiff springs make every stroke violent
        # (bouncing/flipping). Soft spring + moderate servo = smooth tracking.
        self.fly.add_joints(self.skeleton, neutral_pose=KinematicPosePreset.NEUTRAL,
                            stiffness=1.0, damping=0.3, armature=2e-4)
        all_dofs = list(self.skeleton.iter_jointdofs(self.fly.root_segment))
        self.actuated = ActuatedDOFPreset.LEGS_ACTIVE_ONLY.filter(all_dofs)
        # ctrllimited=False: the library would otherwise default actuators to
        # ctrlrange=(0,0), silently clamping every joint target to zero.
        # kp=1e5, kv=1e2: this is a millimeter-scale model (gravity -9810 mm/s^2)
        # where the library-default kp=1 servo is orders of magnitude too weak
        # against the passive joint springs (empirically verified; see
        # EXECUTION_PLAN.md). Without this the fly stands frozen.
        # kp=1e3, kv=10: gravity loads on leg joints are O(1) force units in
        # this mm-scale model; this servo tracks targets smoothly without the
        # violent strokes (bouncing/flipping) that kp=1e5 produced.
        self.fly.add_actuators(self.actuated, ActuatorType.POSITION,
                               forcelimited=False, ctrllimited=False,
                               kp=1e3, kv=10.0)
        # tarsal adhesion (PDF Table 1: active tarsal adhesion, F_adh,max = 15 uN).
        # Grip during stance gives the feet the traction flies get from
        # pulvilli/claws; without it a light 1-mm fly just skates.
        self.fly.add_leg_adhesion(gain=1.0)
        self.leg_order = [str(l) for l in self.fly.get_legs_order()]
        world = FlatGroundWorld()
        import mujoco as _mj
        # lighting for offscreen/video rendering (interactive viewer adds its own
        # headlight; the saved-video path has none, so the scene renders dark)
        world.mjcf_root.worldbody.add_light(
            name="top_light", pos=[0, 0, 30], dir=[0, 0, -1],
            type=int(_mj.mjtLightType.mjLIGHT_DIRECTIONAL), intensity=3.0)
        world.mjcf_root.worldbody.add_light(
            name="fill_light", pos=[10, -10, 15], dir=[-0.5, 0.5, -1],
            type=int(_mj.mjtLightType.mjLIGHT_DIRECTIONAL), intensity=1.2)
        # stimulus objects (banana / predator) as mocap bodies
        for spec in self.stim_mgr.mocap_bodies():
            wb = world.mjcf_root.worldbody.add_body(
                name=spec["name"], pos=spec["pos"], mocap=True)
            if spec.get("kind") == "banana":
                # elongated capsule = banana body; two small brown spheres = tips
                wb.add_geom(type=_mj.mjtGeom.mjGEOM_CAPSULE,
                            size=list(spec["size"]),  # [half-length, radius]
                            rgba=spec["rgba"], contype=0, conaffinity=0,
                            euler=[0, 1.35, 0.35])   # tilted, arc-like
                wb.add_geom(type=_mj.mjtGeom.mjGEOM_SPHERE,
                            size=[spec["size"][1] * 0.8],
                            pos=[spec["size"][0] * 0.95, 0, 0],
                            rgba=spec["tip_rgba"], contype=0, conaffinity=0)
                wb.add_geom(type=_mj.mjtGeom.mjGEOM_SPHERE,
                            size=[spec["size"][1] * 0.8],
                            pos=[-spec["size"][0] * 0.95, 0, 0],
                            rgba=spec["tip_rgba"], contype=0, conaffinity=0)
            else:
                wb.add_geom(type=_mj.mjtGeom.mjGEOM_SPHERE,
                            size=list(spec["size"]),
                            rgba=spec["rgba"], contype=0, conaffinity=0)
        world.add_fly(self.fly,
                      # spawn just above settled stance height (~0.79 mm): a
                      # 1-mm drop with stiff (kp=1e5) servos impacts too hard
                      spawn_position=np.array([0.0, 0.0, 0.82]),
                      spawn_rotation=Rotation3D("quat", [1.0, 0.0, 0.0, 0.0]))
        self.sim = Simulation(world, timestep=PHYSICS_DT)
        # stiff kp=1e5 servos + mm-scale masses: Euler integration destabilizes
        # (QACC NaN). implicitfast is MuJoCo's recommended integrator for stiff
        # joint damping; extra solver iterations harden foot-contact handling.
        import mujoco as _mj2
        self.sim.mj_model.opt.integrator = _mj2.mjtIntegrator.mjINT_IMPLICITFAST
        self.sim.mj_model.opt.iterations = 200
        self.sim.mj_model.opt.ls_iterations = 100
        self.sim.reset()
        self.actuator_type = ActuatorType.POSITION
        self.dof_names = [d.name for d in self.actuated]
        # neutral/rest targets from current angles at reset
        angles = self.sim.get_joint_angles("nmf")
        self.rest = {n: float(a) for n, a in zip(self.dof_names, angles)}
        self.bridge = MotorBridge(self.fly, self.actuated, self.rest)
        # mocap ids for stimulus bodies (mocap_pos is indexed by mocap id,
        # obtained from body_mocapid[body_id])
        self.mocap_ids = {}
        for spec in self.stim_mgr.mocap_bodies():
            bid = _mj.mj_name2id(self.sim.mj_model, _mj.mjtObj.mjOBJ_BODY,
                                 spec["name"])
            mid = int(self.sim.mj_model.body_mocapid[bid])
            self.mocap_ids[spec["name"]] = mid

    # ---------------- metrics (PDF Eqs. 9-13) ----------------
    def _metrics_state(self):
        pos = self.sim.get_body_positions("nmf")
        self._com = np.mean(pos, axis=0)

    def _ground_contacts(self) -> np.ndarray:
        forces, *_ = self.sim.get_ground_contact_info("nmf")
        return (np.abs(np.asarray(forces)) > 1e-6).astype(float)

    def run(self, duration: float = 3.0, render: bool = False, log_every: int = 50,
            settle_s: float = 0.3, viewer=None, sync_every: int = 166,
            camera: str | None = None, out_path: str | None = None,
            video_fps: int = 25, stim_schedule: list | None = None,
            terminate_on: str = "none", timelapse: float = 1.0):
        """Run an embodied trial. First `settle_s` is a settling transient that is
        EXCLUDED from locomotor metrics (the PDF baseline windows ignore
        initial transients).

        terminate_on: "none" (run full duration) | "food" (end trial at
        food_reached -> outcome "survived") | "any" (end at food_reached OR
        death, whichever comes first).

        If `viewer` (a mujoco.viewer handle from launch_passive) is given, the
        live 3D body is synced to it every `sync_every` physics steps (~60 Hz)."""
        n_settle = int(settle_s / NEURAL_DT)
        n_neural_steps = n_settle + int(duration / NEURAL_DT)
        contact_hist = []
        com_hist = []
        tci_hist = []
        dn_hist = []
        cpg_hist = []
        duty_obs = []
        last_drive = 0.5
        speed_hist: list[float] = []
        # survival-assay state
        self._supine_since = None      # t when current supine episode began
        self._supine_total = 0.0       # total time spent flipped
        self._n_flips = 0              # upright -> supine transitions
        self._n_rightings = 0          # supine -> upright recoveries (>=0.25 s)
        self._dead = False
        self._death_t = None
        self._ever_upright = False
        self._upright_frac_numer = 0
        self._upright_frac_denom = 0
        self._last_fly_xy = None
        if stim_schedule:
            for t_onset, kind in stim_schedule:
                self.stim_mgr.schedule(t_onset + settle_s, kind)
        # physics settle at rest pose BEFORE any gait commands: the fly must
        # finish its spawn settling while servos hold neutral, or the gait
        # rides on top of impact dynamics (NaN risk with stiff servos)
        rest_vec = np.array([self.rest[n] for n in self.dof_names])
        n_phys_settle = int(0.25 / PHYSICS_DT)
        for _ in range(n_phys_settle):
            self.sim.set_actuator_inputs("nmf", self.actuator_type, rest_vec)
            self.sim.set_leg_adhesion_states("nmf", np.zeros(6))
            self.sim.step()
            if viewer is not None:
                viewer.sync()
        verbose = viewer is not None   # GUI runs narrate live progress; headless quiet
        next_report_t = 0.0
        recording = camera is not None and out_path is not None
        if recording:
            self.sim.set_renderer(cameras=camera, camera_res=(480, 640),
                                  output_fps=video_fps, playback_speed=max(0.1, float(timelapse)))
        try:
            for step in range(n_neural_steps):
                # 0) fly pose for stimulus geometry + survival assay
                pos = self.sim.get_body_positions("nmf")
                fly_pos = np.asarray(pos[0])
                rot = np.asarray(self.sim.get_body_rotations("nmf"))[0]
                fwd = np.array([1.0, 0.0, 0.0])
                # rotate forward vector by fly quaternion (w,x,y,z)
                w, x, y, z = rot
                R = np.array([
                    [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                    [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                    [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)],
                ])
                fwd = R @ fwd
                # supine (flipped) detection: body up-axis pointing below horizon
                up_z = float((R @ np.array([0.0, 0.0, 1.0]))[2])
                t_sim = step * NEURAL_DT
                # supine detection with HYSTERESIS: enter when clearly inverted
                # (up_z < -0.1), exit only when clearly upright again (up_z >
                # 0.3). Without the band, a rocking fly flickering around the
                # threshold resets the 10 s death timer indefinitely.
                if self._supine_since is not None:
                    supine = up_z < 0.3
                else:
                    supine = up_z < -0.1
                if supine:
                    if self._supine_since is None:
                        self._supine_since = t_sim
                        self._n_flips += 1 if self._ever_upright else 0
                    supine_dur = t_sim - self._supine_since
                    if (not self._dead and supine_dur >= SUPINE_DEATH_S):
                        self._dead = True
                        self._death_t = t_sim
                        self.terminated = "death"
                        self.stim_mgr.history.append(
                            {"event": "death", "t": t_sim,
                             "cause": f"supine {SUPINE_DEATH_S:.0f}s (failed to right)"})
                        if verbose:
                            print(f"\n  *** DIED at t={t_sim:.1f}s sim time "
                                  f"(on its back >= {SUPINE_DEATH_S:.0f}s) ***",
                                  flush=True)
                else:
                    if self._supine_since is not None:
                        supine_dur = t_sim - self._supine_since
                        self._supine_total += supine_dur
                        if supine_dur >= 0.25 and self._ever_upright:
                            self._n_rightings += 1
                        self._supine_since = None
                    self._ever_upright = True
                self._upright_frac_denom += 1
                self._upright_frac_numer += 0 if supine else 1
                # 1) stimuli update -> neural stimulus drives
                if verbose and t_sim >= next_report_t:
                    next_report_t = t_sim + 1.0
                    if supine and not self._dead:
                        print(f"  [t={t_sim:5.1f}s sim] FLY ON ITS BACK - death in "
                              f"{max(0.0, SUPINE_DEATH_S - (t_sim - self._supine_since)):4.1f}s "
                              "(fly time)", flush=True)
                    elif self._dead:
                        print(f"  [t={t_sim:5.1f}s sim] dead - body limp", flush=True)
                    else:
                        print(f"  [t={t_sim:5.1f}s sim] upright, walking", flush=True)
                stim_signals = self.stim_mgr.update(t=step * NEURAL_DT,
                                                    fly_pos=fly_pos,
                                                    fly_forward=fwd,
                                                    dn_drive=last_drive)
                feeding = bool(stim_signals.get("feeding"))
                self.neural.apply_stim(food_gain=stim_signals["food_gain"],
                                       predator_intensity=stim_signals["predator_intensity"],
                                       # no steering while feeding: a standing fly
                                       # must not keep rotating around the food
                                       turn_bias=0.0 if feeding
                                       else stim_signals.get("turn_bias", 0.0))
                # reaching the banana ends the journey (outcome
                # "survived"); with terminate_on="any" a supine death also ends
                # the trial (outcome "death").
                if terminate_on in ("food", "any") and any(
                        e.get("event") == "food_reached"
                        for e in stim_signals.get("events", [])):
                    self.terminated = "survived"
                    if verbose:
                        print(f"\n  *** SURVIVED - reached the food at "
                              f"t={t_sim:.1f}s sim time ***", flush=True)
                    break
                if terminate_on == "any" and self._dead:
                    break
                # move mocap bodies (stimuli visuals)
                mocap_pos = self.stim_mgr.mocap_positions()
                if mocap_pos:
                    mdata = self.sim.mj_data
                    for name, p in mocap_pos.items():
                        mid = self.mocap_ids.get(name)
                        if mid is not None and mid >= 0:
                            mdata.mocap_pos[mid] = p
                # 2) brain step (FlyWire adjacency)
                if stim_signals.get("feeding"):
                    # reached food: feeding state - suppress attractant drive and
                    # hold stepping drive low (fly stands and feeds; a predator
                    # still interrupts, handled in stimuli.update)
                    self.neural.stim_food = 0.0
                    self.neural.stim_predator = 0.0
                self.neural.step()
                dn_drive = self.neural.descending_output(self.dn)
                if self._dead:
                    dn_drive = 0.0   # dead: nervous system offline, body goes limp
                if feeding:
                    # stand-and-feed: FULL locomotor stop. The old min(dn, 0.12)
                    # clamp was not a stop: compute_targets maps mn_rate straight
                    # to stroke amplitude, so 0.12 left a 12%-amplitude gait
                    # running and the fly crept/orbited the banana forever.
                    # (Retained as a hard gate in case the reach event is missed;
                    # normally the trial ENDS at the reach, see above.)
                    dn_drive = 0.0
                last_drive = dn_drive
                # 3) CPG step: descending drive sets stepping frequency;
                #    H1: GABA/Rdl block attenuates inter-leg coupling (PDF Eq. 5)
                turn = float(np.clip(self.neural.turn_bias * 0.6, -1, 1))
                cpg_drive = float(np.clip(dn_drive * self.cpg_drive_gain, 0.0, 2.0))
                # looming panic: the looming->escape command (von Reyn 2017, C183)
                # adds a transient burst on top of the ongoing walk drive, so the
                # escape is a visible bolt (stepping frequency -> cap) rather
                # than a subtle speedup hidden by network averaging.
                if stim_signals["predator_intensity"] > 0:
                    cpg_drive = min(2.0, cpg_drive + 0.35 * stim_signals["predator_intensity"])
                theta = self.cpg.step(NEURAL_DT, drive=cpg_drive,
                                      phi_gaba_block=self.phi_gaba)
                theta_map = {l: theta[i] for i, l in enumerate(LEGS)}
                # 4) joint targets (PDF Eqs. 6-7); H2: para/nAChR scale amplitude
                targets = self.bridge.compute_targets(
                    NEURAL_DT, theta_map, mn_rate=dn_drive,
                    para_scale=self.para_scale * self.cpg_drive_gain,
                    turn=turn)
                # 4) physics: 10 substeps at 1e-4
                target_vec = np.array([targets[n] for n in self.dof_names])
                for phys_i in range(STEPS_PER_NEURAL):
                    self.sim.set_actuator_inputs("nmf", self.actuator_type, target_vec)
                    self.sim.step()
                    if viewer is not None and phys_i % sync_every == 0:
                        if not viewer.is_running():
                            raise KeyboardInterrupt("viewer closed")
                        viewer.sync()
                    if recording:
                        self.sim.render_as_needed()
                # 6) metrics (after settling transient only)
                if step < n_settle:
                    continue
                speed_hist.append(float(np.linalg.norm(
                    (fly_pos[:2] - self._last_fly_xy) / NEURAL_DT)) \
                    if self._last_fly_xy is not None else 0.0)
                self._last_fly_xy = np.array(fly_pos[:2])
                c = self._ground_contacts()
                if c.sum() == 0:
                    # airborne: carry forward last grounded pattern so duty/TCI
                    # reflect the gait, not ballistic flight phases
                    c = contact_hist[-1] if contact_hist else c
                contact_hist.append(c)
                pos = self.sim.get_body_positions("nmf")
                com_hist.append(np.mean(pos, axis=0))
                t1 = [c[LEGS.index(l)] for l in TRIPOD1]
                t2 = [c[LEGS.index(l)] for l in TRIPOD2]
                tci_hist.append(abs(np.mean(t1) - np.mean(t2)))
                dn_hist.append(dn_drive)
                cpg_hist.append(self.cpg.tripod_sync_error())
                duty_obs.append(c)
                if render:
                    self.sim.render_as_needed()
        finally:
            if recording:
                try:
                    self.sim.renderer.save_video(out_path)
                    print(f"video saved: {out_path}")
                except Exception as e:  # noqa: BLE001
                    print(f"video save failed: {type(e).__name__}: {e}")
        contacts = np.array(contact_hist) if contact_hist else np.zeros((0, 6))
        com = np.array(com_hist) if com_hist else np.zeros((0, 3))
        # flygym positions are ALREADY in mm (verified against the 1-mm-scale
        # model: thorax z ~ 0.37). Do NOT rescale.
        T = len(com_hist) * NEURAL_DT
        vx = float((com[-1][0] - com[0][0]) / T) if len(com) > 1 else 0.0
        path = np.sum(np.linalg.norm(np.diff(com, axis=0), axis=1)) if len(com) > 1 else 0.0
        straight = (float(np.linalg.norm(com[-1] - com[0]) / path)
                    if path > 1e-9 else 0.0)
        duty = (np.mean(contacts, axis=0) if len(contacts) else np.zeros(6)).tolist()
        per_leg_contact = contacts.mean(axis=0) if len(contacts) else np.zeros(6)
        tripod_members = [LEGS.index(l) for l in TRIPOD1]
        tci = float(np.mean(tci_hist)) if tci_hist else 0.0
        metrics = {
            "drug": self.drug_name,
            "dose": self.mod["dose"],
            "duration_s": duration,
            "vx_mm_s": vx,                    # mm/s (flygym positions are mm)
            "straightness_index": straight,
            "tripod_coordination_index": tci,
            "duty_factor_per_leg": duty,
            "mean_dn_rate": float(np.mean(dn_hist)) if dn_hist else 0.0,
            "mean_cpg_sync_error": float(np.mean(cpg_hist)) if cpg_hist else 0.0,
            "mean_activation": self.bridge.mean_activation(),
            "para_scale": self.para_scale,
            "phi_gaba_effective": self.phi_gaba,
            "n_flywire_neurons": self.neural.n,
            "n_descending_neurons": int(len(self.dn)),
            "final_com_mm": com[-1].tolist() if len(com) else None,
            "stimulus_events": self.stim_mgr.history,
            "reaction_times": self.stim_mgr.reaction_times(),
            "feeding_at_end": bool(self.stim_mgr.feeding),
            "terminated": self.terminated,
            "outcome": ("death" if self._dead else
                        "survived" if self.terminated == "survived"
                        else "completed"),
            "trial_id": self.trial_id,
            "cpg_drive_gain": self.cpg_drive_gain,
            # ---- survival & motion-timing assay ----
            "survival": {
                "alive": not self._dead,
                "death_t": self._death_t,
                "death_cause": (f"supine >={SUPINE_DEATH_S:.0f}s"
                                if self._dead else None),
                "n_flips": self._n_flips,
                "n_rightings": self._n_rightings,
                "time_supine_s": round(self._supine_total, 3),
                "upright_fraction": round(
                    self._upright_frac_numer / max(1, self._upright_frac_denom), 3),
            },
            "speed_profile": {
                "mean_mm_s": round(float(np.mean(speed_hist)), 2) if speed_hist else 0.0,
                "peak_mm_s": round(float(np.max(speed_hist)), 2) if speed_hist else 0.0,
                "p90_mm_s": round(float(np.percentile(speed_hist, 90)), 2) if speed_hist else 0.0,
                "n_samples": len(speed_hist),
            },
        }
        # per-trial data report: death and food-reach both emit data
        try:
            from datetime import datetime, timezone
            report = {
                "trial_id": self.trial_id,
                "recorded_utc": datetime.now(timezone.utc).isoformat(),
                "outcome": metrics["outcome"],
                "terminated": self.terminated,
                "drug": self.drug_name,
                "dose": self.mod["dose"],
                "death": metrics["survival"],
                "stimulus_events": self.stim_mgr.history,
                "reaction_times": self.stim_mgr.reaction_times(),
                "key_metrics": {k: metrics[k] for k in (
                    "vx_mm_s", "straightness_index", "tripod_coordination_index",
                    "mean_dn_rate", "speed_profile") if k in metrics},
            }
            out_dir = Path("results")
            out_dir.mkdir(exist_ok=True)
            (out_dir / f"{self.trial_id}.json").write_text(json.dumps(report, indent=2))
            metrics["report_path"] = str(out_dir / f"{self.trial_id}.json")
        except Exception as e:  # noqa: BLE001 - reporting must never break the sim
            metrics["report_path"] = f"(report write failed: {type(e).__name__}: {e})"
        return metrics, {"contacts": contacts, "com": com, "tci": tci_hist,
                         "dn": dn_hist}

    def close(self):
        try:
            self.sim.close()
        except Exception:
            pass


if __name__ == "__main__":
    for drug in (None, "Caffeine", "Lidocaine", "Dormiphen (Sleeping Pill)"):
        s = DrugBodySim(drug_name=drug)
        m, _ = s.run(duration=1.0)
        print(json.dumps(m, indent=2)[:700])
        print("---")
        s.close()
