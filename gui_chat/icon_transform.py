import base64

def image_to_py(image_path, py_file_name):
    """Конвертирует картинку в Python-файл с Base64 строкой"""
    
    # Читаем картинку как бинарный файл
    with open(image_path, 'rb') as f:
        # Конвертируем в Base64 строку
        data = base64.b64encode(f.read()).decode('utf-8')
    
    # Создаем Python-файл с этой строкой
    with open(py_file_name, 'w', encoding='utf-8') as f:
        f.write(f'# Этот файл создан автоматически\n')
        f.write(f'# Не редактируйте вручную!\n\n')
        f.write(f'image_data = """{data}"""\n')
    
    print(f'✅ Файл {image_path} сконвертирован в {py_file_name}')
    print(f'   Размер строки Base64: {len(data)} символов')

image_to_py('info_icon.png', 'icon_data.py')