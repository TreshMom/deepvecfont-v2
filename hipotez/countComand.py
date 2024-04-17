import re

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

total_commands = 0

# Проходим по каждому SVG и считаем количество команд
for svg_id, commands_list in svg_commands.items():
    total_commands += len(commands_list)

print("Общее количество команд для всех SVG:", total_commands)