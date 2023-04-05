import numpy as np
from matplotlib.patches import Circle

from ese200.config import Config


class Simulator:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.A, self.B = get_dynamics(config.time_step)
        self.rng = np.random.default_rng()

    def step(self, x, u):
        noise = self.rng.normal(
            scale=self.config.trajectory_noise * self.config.time_step, size=x.shape
        )
        return x @ self.A.T + u @ self.B.T + noise


def plot_obstacles(ax):
    config = Config()
    ax.set_aspect("equal")
    for i in range(2):
        for j in range(2):
            ax.add_patch(
                Circle(
                    (
                        config.trajectory_radius * (2 * i),
                        config.trajectory_radius * (2 * j),
                    ),
                    config.trajectory_radius - config.trajectory_margin,
                    color="k",
                    fill=False,
                )
            )


def generate_expert_trajectories():
    rng = np.random.default_rng()
    config = Config()
    A, B = get_dynamics(config.time_step)
    t = np.arange(0, config.duration, config.time_step)
    x = np.zeros((config.n_trajectories, len(t), 4))
    u = np.zeros((config.n_trajectories, len(t), 2))

    # generate random trajectories
    points = (
        np.asarray(
            [
                [-1, 0],
                [-1, 2],
                [0, 3],
                [1, 2],
                [1, 1],
                [2, 1],
                [3, 0],
                [2, -1],
                [0, -1],
            ]
        )
        * config.trajectory_radius
    )
    points = points[None, ...] + rng.normal(
        scale=config.trajectory_noise,
        size=(config.n_trajectories,) + points.shape,
    )

    for i in range(config.n_trajectories):
        x[i], u[i] = optimize(A, B, t, points[i])

    noise = rng.normal(scale=config.state_noise * config.time_step, size=x.shape)
    return x + noise, u, points


def optimize(A, B, t, points):
    """
    Fit a polynomial trajectory to a set of points.
    Find a trajectory that goes through all the points.
    The trajectory should have minimum acceleration.
    """
    import cvxpy as cp

    u = cp.Variable((len(t), 2))
    x = cp.Variable((len(t), 4))

    # assume we pass through all points at equal time intervals
    # we also assume that the first point is also the last point for loop closure
    point_idx = np.linspace(0, len(t) - 1, len(points) + 1).astype(int)[:-1]
    point_idx[0] = 0

    # objective is to minimize the sum of squared accelerations
    objective = cp.sum_squares(u)
    constraints = [
        # dynamics
        x[1:] == x[:-1] @ A.T + u[:-1] @ B.T,
        # pass through points
        x[point_idx, :2] == points,
        # final state should be equal to initial state
        x[-1] == x[0],
    ]

    # solve optimization problem
    prob = cp.Problem(cp.Minimize(objective), constraints)
    prob.solve()
    return x.value, u.value


def get_dynamics(dt: float):
    # Define dynamical model parameters
    # This is a 2D model with position and velocity
    # state x = [x, y, vx, vy]
    # input u = [ax, ay]
    A = np.array(
        [
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
    )
    # Input is acceleration
    B = np.array(
        [
            [0.5 * dt**2, 0.0],
            [0.0, 0.5 * dt**2],
            [dt, 0.0],
            [0.0, dt],
        ]
    )
    return A, B


if __name__ == "__main__":
    x, u, points = generate_expert_trajectories()
    np.save("data/states.npy", x)
    np.save("data/inputs.npy", u)
