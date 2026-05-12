import numpy as np
import matplotlib.pyplot as plt
import acts


def computer_helix(t, radius=1, pitch=0.5):
    return np.array([radius * np.cos(t), radius * np.sin(t), pitch * t])


fig, ax = plt.subplots(subplot_kw={"projection": "3d"})

b_field = np.array([0, 0, 1])

ts = np.linspace(0, 2 * np.pi, 100)
helix = computer_helix(ts)

ax.plot(helix[0], helix[1], helix[2], color="k", zorder=1)

sp0 = helix[:, 0]
sp1 = helix[:, 15]
sp2 = helix[:, 30]
sps = np.array([sp0, sp1, sp2])

ax.scatter(sps[:, 0], sps[:, 1], sps[:, 2], color="r", zorder=5)

tangent0, tangent1, tangent2 = acts.estimateTrackTangentsFromSeed(
    acts.Vector3(sp0), acts.Vector3(sp1), acts.Vector3(sp2), acts.Vector3(b_field)
)
tangent0 = np.array(tangent0)
tangent1 = np.array(tangent1)
tangent2 = np.array(tangent2)

ax.plot(
    *np.array([sp0 - 0.25 * tangent0, sp0 + 0.25 * tangent0]).T, color="C0", zorder=3
)
ax.plot(
    *np.array([sp1 - 0.25 * tangent1, sp1 + 0.25 * tangent1]).T, color="C1", zorder=3
)
ax.plot(
    *np.array([sp2 - 0.25 * tangent2, sp2 + 0.25 * tangent2]).T, color="C2", zorder=3
)

ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)
ax.set_zlim(-3, 3)

ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_zlabel("z")

plt.show()
