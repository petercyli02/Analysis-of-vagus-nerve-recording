import numpy as np
import csv

duration = 8895  # For rat7&8_Day2_noSound
period = 300
mn, mx = 70, 170

n = duration // period

y = np.random.uniform(low=mn, high=mx, size=n)
x = np.linspace(0, duration, n, dtype=np.float32)
# print(type(x[0]))
# print(type(y[0]))

with open('../../datasets/rat7&8/day2/dummy_glucose_data.csv', 'w', newline='') as file:
    writer = csv.writer(file, delimiter=',')
    for i in range(len(y)):
        writer.writerow([x[i], y[i]])

# with open('dummy_glucose_data.csv', 'w', newline='') as file:
#     writer = csv.writer(file, delimiter=',')
#     for i in range(8895):
#         writer.writerow([i, i * 2])