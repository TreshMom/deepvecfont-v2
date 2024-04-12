import re

with open("resultItalic100.html", "r") as file:
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
        
        # Находим все команды "M" в атрибуте "d"
        m_commands = re.findall(r'M\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)', path_data)

        # Находим все команды "L" в атрибуте "d"
        l_commands = re.findall(r'L\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)', path_data)
        
        # Находим все команды "C" в атрибуте "d"
        c_commands = re.findall(r'C\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)', path_data)
        
        # Добавляем информацию о командах в словарь
        svg_commands[f'SVG {i}'] = {
            'M': [{'x': float(x), 'y': float(y)} for x, y in m_commands],
            'L': [{'x': float(x), 'y': float(y)} for x, y in l_commands],
            'C': [{'x1': float(x1), 'y1': float(y1), 'x2': float(x2), 'y2': float(y2), 'x3': float(x3), 'y3': float(y3)} for x1, y1, x2, y2, x3, y3 in c_commands]
        }

"""
# Выводим полученный словарь
for svg_name, commands_info in svg_commands.items():
    print(f"{svg_name}:")
    for command_type, points_list in commands_info.items():
        print(f"{command_type}:")
        for point in points_list:
            print(point)
        print()
"""
"""
for svg_name, commands_info in svg_commands.items():
    print(f"{svg_name}:")
    for command_type, points_list in commands_info.items():
        print(f"{command_type}: {len(points_list)}")
    print()
"""
# Вывод информации только о первом и пятомдесят втором элементах SVG
for svg_name, commands_info in svg_commands.items():
    if svg_name == 'SVG 1' or svg_name == 'SVG 53':
        print(f"{svg_name}:")
        for command_type, points_list in commands_info.items():
            print(f"{command_type}: {len(points_list)}")
            for point in points_list:
                print(point)
        print()
