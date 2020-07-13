import numpy as np
import matplotlib.pyplot as plt

X = np.array([0,
25,
50,
75,
90,
100,
])

Y = np.array([1.25277876853943,
2.0035707950592,
2.50485920906067,
32.0560462474823,
38.8137402534485,
100
])

plt.plot(X, Y, color="red", marker="+")
plt.xlabel("loss %")
plt.ylabel("transmission time")
plt.plot(X, Y)
plt.show()
