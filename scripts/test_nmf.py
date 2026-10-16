#!/usr/bin/env python3
"""Smoke test for NeuroMechFly v2 (flygym 2.1.0 composition API) on macOS/headless.

Verifies: model compiles, physics steps at dt=1e-4, leg contact sensors report,
position-actuator (PD servo) control path works, offscreen render attempt.
"""
import numpy as np

from flygym import Simulation
from flygym.anatomy import ActuatedDOFPreset, AxisOrder, JointPreset, Skeleton
from flygym.compose import (
    ActuatorType,
    FlatGroundWorld,
    KinematicPosePreset,
    NeuroMechFly,
)
from flygym.utils.math import Rotation3D


def main():
    fly = NeuroMechFly(name="nmf")

    skeleton = Skeleton(
        axis_order=AxisOrder.DONTCARE,
        joint_preset=JointPreset.LEGS_ACTIVE_ONLY,
    )
    fly.add_joints(skeleton, neutral_pose=KinematicPosePreset.NEUTRAL)

    all_dofs = list(skeleton.iter_jointdofs(fly.root_segment))
    actuated = ActuatedDOFPreset.LEGS_ACTIVE_ONLY.filter(all_dofs)
    print(f"joint DOFs: {len(all_dofs)}, actuated (legs active): {len(actuated)}")

    # Position actuators = MuJoCo PD servos (theta_target drive, PDF Eq. 8)
    fly.add_actuators(actuated, ActuatorType.POSITION, forcerange=(-30.0, 30.0))

    world = FlatGroundWorld()
    world.add_fly(
        fly,
        spawn_position=np.array([0.0, 0.0, 1.0]),
        spawn_rotation=Rotation3D("quat", [1.0, 0.0, 0.0, 0.0]),
    )

    sim = Simulation(world, timestep=1e-4)  # PDF: dt = 1e-4 s
    sim.reset()

    n_act = len(fly.get_actuated_jointdofs_order(ActuatorType.POSITION))
    print("n position actuators:", n_act)

    rest = np.zeros(n_act)
    for i in range(2000):  # 0.2 s
        sim.set_actuator_inputs("nmf", ActuatorType.POSITION, rest)
        sim.step()
        if i % 500 == 0:
            angles = sim.get_joint_angles("nmf")
            print(
                f"step {i:5d} t={sim.time*1e3:7.2f} ms  "
                f"mean|angle|={np.mean(np.abs(angles)):.4f} rad"
            )

    forces, force_pos, *_ = sim.get_ground_contact_info("nmf")
    print("per-leg contact |F|:", np.round(np.abs(forces), 4))
    print(f"total |F| across legs: {float(np.abs(forces).sum()):.4f}")

    try:
        sim.set_renderer(cameras=[], camera_res=(240, 320))
        sim.render_as_needed()
        print("render OK")
    except Exception as e:  # noqa: BLE001
        print("render unavailable (headless):", type(e).__name__, str(e)[:120])

    print("NMF SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
