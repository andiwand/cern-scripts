import re

p = re.compile(
    r"Find track with entry index = (\d+) and there are nMeasurements = (\d+), nOutliers = (\d+), nHoles = (\d+) on track"
)

matches = []
for line in open("debug-log.txt"):
    for f in p.findall(line):
        matches.append(tuple(map(int, f)))

print(len(matches))

import numpy as np
import matplotlib.pyplot as plt

matches = np.array(matches)

plt.hist(matches[:, 1], label="nMeasurements")
plt.hist(matches[:, 2], label="nOutliers")
plt.hist(matches[:, 3], label="nHoles")
plt.hist(np.sum(matches[:, 1:], axis=1), label="nTotal")
plt.legend()
plt.show()
