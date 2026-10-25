# Лабораторные работы по PyQt5

Каждая работа находится в своей папке. В корне используются общие окружение Python и зависимости.

| Папка | Работа |
| --- | --- |
| `lr1` | Окно с переключением текста и картинки |
| `lr2` | «Термостанция»: три связанных поля, сигналы и слоты |

## Запуск на Windows

Откройте корневую папку проекта в VS Code. В терминале PowerShell выполните:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe lr2/main.py
```

Если окружения ещё нет, сначала создайте его командой `py -m venv .venv`.

Для первой работы используйте:

```powershell
.\.venv\Scripts\python.exe lr1/main.py
```

Через **Ctrl+Shift+P → Python: Select Interpreter** выберите `.venv\Scripts\python.exe`. В `.vscode/launch.json` приложены отдельные конфигурации запуска для обеих работ.

Устанавливать отдельное окружение для каждой лабораторной не требуется. Окружение и `__pycache__` исключены из Git в `.gitignore`.
