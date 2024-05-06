import numpy as np

# Загрузка данных из файла class.npy
class_data = np.load('TT Autonomous Mono Italic  NPY/pts_aux.npy')
z = np.load('TT Autonomous Mono Italic  NPY/sequence.npy')
# у А 16 команд
#print(class_data.shape)
"""
count = 0
command = 0
for i in range(len(class_data[0])):
    if class_data[0][i] > 1:
        count += 1
    if class_data[0][i] == 1:
        command += 1
print(class_data[0])
print(command, count)
"""
print(z[0])
print(class_data[0])