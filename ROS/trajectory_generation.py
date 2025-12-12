#!/usr/bin/env python3
"""
trajectory_generation.py
Generate a time-parameterized trajectory from a smooth path.
"""

import numpy as np

def generate_trajectory(path, dt=0.1, v=0.2):
    """
    path: list of (x, y) tuples
    dt: timestep
    v: constant linear velocity
    returns: list of (x, y, t) tuples
    """
    traj = []
    t_curr = 0.0

    for i in range(1, len(path)):
        x0, y0 = path[i-1]
        x1, y1 = path[i]
        dist = np.hypot(x1-x0, y1-y0)
        if dist < 1e-6:
            continue
        n_steps = max(int(np.ceil(dist/(v*dt))), 1)
        for j in range(n_steps):
            s = j/n_steps
            x = x0 + s*(x1-x0)
            y = y0 + s*(y1-y0)
            traj.append((x, y, t_curr))
            t_curr += dt

    traj.append((path[-1][0], path[-1][1], t_curr))
    return traj
