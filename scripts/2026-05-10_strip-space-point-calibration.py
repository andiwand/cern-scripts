import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


fig, ax = plt.subplots(subplot_kw={"projection": "3d"})

phi = Slider(
    ax=fig.add_axes([0.1, 0.9, 0.2, 0.03]),
    label="phi",
    valmin=-np.pi,
    valmax=np.pi,
    valinit=np.pi / 2,
)
theta = Slider(
    ax=fig.add_axes([0.1, 0.85, 0.2, 0.03]),
    label="theta",
    valmin=0,
    valmax=np.pi,
    valinit=np.pi / 2,
)

separation = Slider(
    ax=fig.add_axes([0.7, 0.9, 0.2, 0.03]),
    label="separation",
    valmin=0,
    valmax=1,
    valinit=0.1,
)
alpha = Slider(
    ax=fig.add_axes([0.7, 0.85, 0.2, 0.03]),
    label="alpha",
    valmin=0,
    valmax=1,
    valinit=0.1,
)

def inner_vectors():
    return np.array([[0, 0, -1], [0, 0, 1]])

def outer_vectors(separation, alpha):
    outer_vectors = inner_vectors() + np.array([0, separation, 0])
    # rotate by alpha around y axis
    c, s = np.cos(alpha), np.sin(alpha)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return outer_vectors @ R.T

inner, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="C0")
outer, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="C1")
direction, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="k")
point_inner, = ax.plot([0], [0], [0], "o", lw=4, color="r")
point_outer, = ax.plot([0], [0], [0], "o", lw=4, color="r")
point_direction, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="r")

def update(_):
    iv = inner_vectors()
    ov = outer_vectors(separation.val, alpha.val)
    dv = np.array([np.cos(phi.val) * np.sin(theta.val), np.sin(phi.val) * np.sin(theta.val), np.cos(theta.val)])

    inner.set_data(iv[:, :2].T)
    inner.set_3d_properties(iv[:, 2])

    outer.set_data(ov[:, :2].T)
    outer.set_3d_properties(ov[:, 2])

    direction.set_data([0.5, 0.5 + 0.5 * dv[0]], [0.5, 0.5 + 0.5 * dv[1]])
    direction.set_3d_properties([0.5, 0.5 + 0.5 * dv[2]])

    icv = 0.5 * (iv[0] + iv[1])
    ihv = 0.5 * (iv[1] - iv[0])
    ocv = 0.5 * (ov[0] + ov[1])
    ohv = 0.5 * (ov[1] - ov[0])
    scd = ocv - icv

    d_outer = np.cross(ohv, dv)
    scale = np.dot(ihv, d_outer)
    s_inner = np.dot(scd, d_outer) / scale
    d_inner = np.cross(ihv, dv)
    s_outer = np.dot(scd, d_inner) / scale

    cal_inner = icv + s_inner * ihv
    cal_outer = ocv + s_outer * ohv

    point_inner.set_xdata([cal_inner[0]])
    point_inner.set_ydata([cal_inner[1]])
    point_inner.set_3d_properties([cal_inner[2]])
    point_outer.set_xdata([cal_outer[0]])
    point_outer.set_ydata([cal_outer[1]])
    point_outer.set_3d_properties([cal_outer[2]])

    pdv = cal_outer - cal_inner
    pdv /= np.linalg.norm(pdv)
    pdvs = np.array([cal_inner - 0.5 * pdv, cal_outer + 0.5 * pdv])

    point_direction.set_data(pdvs[:, 0], pdvs[:, 1])
    point_direction.set_3d_properties(pdvs[:, 2])

    fig.canvas.draw_idle()
update(None)

phi.on_changed(update)
theta.on_changed(update)
separation.on_changed(update)
alpha.on_changed(update)

ax.set_xlim(-1, 1)
ax.set_ylim(-1, 1)
ax.set_zlim(-1, 1)

plt.show()
