import numpy as np
import matplotlib.pyplot as plt
import scipy.stats

std_x, std_y, rho = 10, 3, 1
n = 100000

mean = [0, 0]
cov = [[std_x * std_x, rho * std_x * std_y], [rho * std_x * std_y, std_y]]

x = np.random.multivariate_normal(mean, cov, n)

r = x - mean
p = r / np.array([std_x, std_y])

plt.figure(0)
plt.title("dist")
plt.axis("equal")
plt.hist2d(x[:, 0], x[:, 1], bins=100)

plt.figure(1)
plt.title("pulls")
plt.hist2d(p[:, 0], p[:, 1], bins=100)

plt.figure(2)
plt.title("pulls x")
plt.hist(p[:, 0], bins=40, density=True)
x = np.linspace(-4, 4, 1000)
plt.plot(x, scipy.stats.norm.pdf(x))

plt.figure(3)
plt.title("pulls y")
plt.hist(p[:, 0], bins=40, density=True)
x = np.linspace(-4, 4, 1000)
plt.plot(x, scipy.stats.norm.pdf(x))

plt.show()
