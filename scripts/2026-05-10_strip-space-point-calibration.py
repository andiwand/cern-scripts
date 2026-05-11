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
#direction_x, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
#direction_y, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
#direction_z, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
direction_xy, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
direction_xz, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
direction_yz, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="grey")
point_inner, = ax.plot([0], [0], [0], "o", lw=4, color="r")
point_outer, = ax.plot([0], [0], [0], "o", lw=4, color="r")
point_direction, = ax.plot([0, 0], [0, 0], [0, 0], lw=2, color="r")

def update(_):
    iv = inner_vectors()
    ov = outer_vectors(separation.val, alpha.val)
    dv = np.array([np.cos(phi.val) * np.sin(theta.val), np.sin(phi.val) * np.sin(theta.val), np.cos(theta.val)])

    def set_data(line, data):
        line.set_data(data[:, :2].T)
        line.set_3d_properties(data[:, 2])

    set_data(inner, iv)
    set_data(outer, ov)

    dir_center = np.array([-0.75, 0.75, -0.75])
    set_data(direction, np.array([dir_center - 0.25 * dv, dir_center + 0.25 * dv]))
    #set_data(direction_x, np.array([dir_center, dir_center]) + np.array([[-0.25 * dv[0], 0.25, -0.25], [0.25 * dv[0], 0.25, -0.25]]))
    #set_data(direction_y, np.array([dir_center, dir_center]) + np.array([[-0.25, -0.25 * dv[1], -0.25], [-0.25, 0.25 * dv[1], -0.25]]))
    #set_data(direction_z, np.array([dir_center, dir_center]) + np.array([[-0.25, 0.25, -0.25 * dv[2]], [-0.25, 0.25, 0.25 * dv[2]]]))
    set_data(direction_xy, np.array([dir_center, dir_center]) + np.array([[-0.25 * dv[0], -0.25 * dv[1], -0.25], [0.25 * dv[0], 0.25 * dv[1], -0.25]]))
    set_data(direction_xz, np.array([dir_center, dir_center]) + np.array([[-0.25 * dv[0], 0.25, -0.25 * dv[2]], [0.25 * dv[0], 0.25, 0.25 * dv[2]]]))
    set_data(direction_yz, np.array([dir_center, dir_center]) + np.array([[-0.25, -0.25 * dv[1], -0.25 * dv[2]], [-0.25, 0.25 * dv[1], 0.25 * dv[2]]]))

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

    set_data(point_inner, cal_inner[None])
    set_data(point_outer, cal_outer[None])

    pdv = cal_outer - cal_inner
    pdv /= np.linalg.norm(pdv)
    pdvs = np.array([cal_inner - 0.5 * pdv, cal_outer + 0.5 * pdv])

    set_data(point_direction, pdvs)

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
