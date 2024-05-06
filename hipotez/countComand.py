import re
import matplotlib.pyplot as plt

with open("hipotez/resultItalic100.html", "r") as file:
    html_content = file.read()

# Разбиваем HTML-контент на строки, начинающиеся с тега <svg
svg_strings = html_content.split("<svg")

# Создаем пустой словарь для хранения информации о командах для каждого элемента SVG
svg_commands = {}

# Найти атрибут "d" и извлечь его значение для каждого элемента SVG
for i in range(1, len(svg_strings)):
    path_data_match = re.search(r'd="([^"]+)"', svg_strings[i])
    if path_data_match:
        path_data = path_data_match.group(1)
        
        # Находим все команды в атрибуте "d"
        commands = re.findall(r'([MLC])\s*([-+]?\d*\.?\d*)\s+([-+]?\d*\.?\d*)', path_data)

        # Добавляем информацию о командах в словарь
        svg_commands[f'SVG {i}'] = [{'command': cmd, 'x': float(x), 'y': float(y)} for cmd, x, y in commands]

for i in range(1, 52):
    predict = svg_commands[f'SVG {i}']
    origin = svg_commands[f'SVG {i + 52}']
    print(len(predict[0]))
    #s = []
    #s.append()
"""
i = 1
print(len(svg_commands[f'SVG {i}']))
a = svg_commands['SVG 1'][1]
print(a)
print(a['y'])
"""
leng = 0
sumary = 0
coc = 0
for i in range(1, 52):
    predict = svg_commands[f'SVG {i}']
    origin = svg_commands[f'SVG {i + 52}']
    for j in range (0, min(len(predict), len(origin))):
        if predict[j]['command'] == origin[j]['command']:
            a = predict[j]['x'] - origin[j]['x'], predict[j]['y'] - origin[j]['y']
            print(a)
            sumary += 1
            if (-1 <= a[0] <= 1) and (-1 <= a[1] <= 1):
                leng += 1
                if j == 12:
                    coc += 1

print(leng)
print(sumary)
print(coc)
"""
total_commands = 0

# Проходим по каждому SVG и считаем количество команд
for svg_id, commands_list in svg_commands.items():
    total_commands += len(commands_list)

print("Общее количество команд для всех SVG:", total_commands)


for i in range(53, 105):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))
    print(f"SVG {i}: {commands_count} команд")
"""

svg_numbers_1 = []
commands_counts_1 = []
svg_numbers_2 = []
commands_counts_2 = []

# Цикл по SVG с номерами от 53 до 104 для первого набора
for i in range(53, 105):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    svg_numbers_1.append(i)  # Добавляем номер SVG в список
    commands_counts_1.append(commands_count)  # Добавляем количество команд в список

# Цикл по SVG с номерами от 1 до 52 для второго набора
for i in range(1, 52):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    svg_numbers_2.append(i)  # Добавляем номер SVG в список
    commands_counts_2.append(commands_count)  # Добавляем количество команд в список

fig, ax = plt.subplots(figsize=(10, 5))

# Первый график
ax.plot(svg_numbers_1, commands_counts_1, marker='o', linestyle='-', color='blue', label='SVG 53-104')

# Второй график
ax.plot(svg_numbers_2, commands_counts_2, marker='o', linestyle='-', color='red', label='SVG 1-51')

# Настроим оси и легенду
ax.set_xlabel('Номер SVG')
ax.set_ylabel('Количество команд')
ax.set_title('Количество команд в каждом SVG')
ax.grid(True)
ax.legend()

# Повернем метки по оси x, чтобы они были легче читаемыми
plt.xticks(rotation=45)

plt.show()


commands_counts_1 = []
commands_counts_2 = []

# Цикл по SVG с номерами от 53 до 104 для первого набора
for i in range(53, 105):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    commands_counts_1.append(commands_count)  # Добавляем количество команд в список

# Цикл по SVG с номерами от 1 до 52 для второго набора
for i in range(1, 53):
    svg_id = f'SVG {i}'
    commands_count = len(svg_commands.get(svg_id, []))  # Получаем количество команд для текущего SVG
    commands_counts_2.append(commands_count)  # Добавляем количество команд в список

# Строим гистограмму
plt.figure(figsize=(10, 5))
plt.hist([commands_counts_1, commands_counts_2], bins=50, label=['SVG 53-104', 'SVG 1-52'])
plt.xlabel('Количество команд')
plt.ylabel('Частота')
plt.title('Гистограмма количества команд в каждом наборе SVG')
plt.legend()
plt.grid(True)

# Отображаем гистограмму
plt.show()