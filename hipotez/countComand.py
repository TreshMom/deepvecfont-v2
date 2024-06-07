import re
import matplotlib.pyplot as plt
import numpy as np

with open("hipotez/classic_500_8_italic.ckpt_syn_merge.html", "r") as file:
    html_content = file.read()
svg_strings = html_content.split("<svg")
svg_commands = {}

# Находим атрибут "d" и извлекаем его значение для каждого элемента SVG
for i in range(1, len(svg_strings)):
    path_data_match = re.search(r'd="([^"]+)"', svg_strings[i])
    if path_data_match:
        path_data = path_data_match.group(1)
        commands = re.findall(r'([MLC])\s*([-+]?\d*\.?\d*)\s+([-+]?\d*\.?\d*)', path_data)
        svg_commands[f'SVG {i}'] = [{'command': cmd, 'x': float(x), 'y': float(y)} for cmd, x, y in commands]

print(f"Total SVGs: {len(svg_commands)}")

# Объединяем предсказанные и оригинальные SVG элементы в одну структуру для удобства
svg_pairs = []
for i in range(1, 53):
    predict_key = f'SVG {i}'
    origin_key = f'SVG {i + 52}'  # Обратите внимание, что мы используем i + 52, а не i + 51
    if predict_key in svg_commands and origin_key in svg_commands:
        svg_pairs.append((svg_commands[predict_key], svg_commands[origin_key]))

print(f"Total pairs: {len(svg_pairs)}")

# Проходим по парам и выводим различия
leng = 0
sumary = 0
coc = 0
for predict, origin in svg_pairs:
    for j in range(min(len(predict), len(origin))):
        if predict[j]['command'] == origin[j]['command']:
            a = predict[j]['x'] - origin[j]['x'], predict[j]['y'] - origin[j]['y']
            print(a)
            sumary += 1
            if (-1 <= a[0] <= 1) and (-1 <= a[1] <= 1):
                leng += 1
                if j == 12:
                    coc += 1

print(f"Total length: {leng}")
print(f"Total summary: {sumary}")
print(f"Total count at index 12: {coc}")


total_commands = sum(len(commands) for commands in svg_commands.values())
print(f"Общее количество команд для всех SVG: {total_commands}")

svg_numbers_1 = []
commands_counts_1 = []
svg_numbers_2 = []
commands_counts_2 = []

# Цикл по SVG с номерами от 1 до 52 для первого набора
for i in range(1, 53):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    svg_numbers_1.append(i)  # Добавляем номер SVG в список
    commands_counts_1.append(commands_count)  # Добавляем количество команд в список

# Цикл по SVG с номерами от 53 до 104 для второго набора
for i in range(53, 105):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    svg_numbers_2.append(i - 52)  # Добавляем номер SVG в список
    commands_counts_2.append(commands_count)  # Добавляем количество команд в список

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(svg_numbers_1, commands_counts_1, marker='o', linestyle='-', color='blue', label='SVG 1-52')
ax.plot(svg_numbers_2, commands_counts_2, marker='o', linestyle='-', color='red', label='SVG 53-104')

ax.set_xlabel('Номер SVG')
ax.set_ylabel('Количество команд')
ax.set_title('Количество команд в каждом SVG')
ax.grid(True)
ax.legend()
plt.xticks(np.arange(1, 52))
plt.yticks(np.arange(1, 30))
plt.show()

plt.figure(figsize=(10, 5))
plt.hist([commands_counts_1, commands_counts_2], bins=50, label=['SVG 1-52', 'SVG 53-104'])
plt.xlabel('Количество команд')
plt.ylabel('Частота')
plt.title('Гистограмма количества команд в каждом наборе SVG')
plt.legend()
plt.grid(True)
plt.show()
