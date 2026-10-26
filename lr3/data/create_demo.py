"""Создание учебной БД с реальными фильмами. Источники — в SOURCES.md."""
import sqlite3
from pathlib import Path


def create_demo(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Файл уже существует: {path}. Укажи новое имя.")
    with sqlite3.connect(path) as db:
        db.executescript('''
            PRAGMA foreign_keys = ON;
            CREATE TABLE directors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT NOT NULL
            );
            CREATE TABLE films (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                year INTEGER NOT NULL,
                genre TEXT NOT NULL,
                duration_min INTEGER NOT NULL CHECK(duration_min > 0),
                rating REAL NOT NULL CHECK(rating BETWEEN 0 AND 10),
                director_id INTEGER NOT NULL REFERENCES directors(id)
            );
            CREATE INDEX idx_films_director ON films(director_id);
            CREATE INDEX idx_films_rating ON films(rating);
            CREATE VIEW film_catalog AS
                SELECT f.title, d.name AS director, f.year, f.genre, f.rating
                FROM films f JOIN directors d ON d.id = f.director_id;
        ''')
        # city — город рождения режиссёра
        db.executemany("INSERT INTO directors VALUES (?, ?, ?)", [
            (1, "Кристофер Нолан", "Лондон"),
            (2, "Джеймс Кэмерон", "Капускасинг"),
            (3, "Роберт Земекис", "Чикаго"),
            (4, "Стивен Спилберг", "Цинциннати"),
            (5, "Хаяо Миядзаки", "Токио"),
            (6, "Квентин Тарантино", "Ноксвилл"),
        ])
        # rating — сохранённая оценка IMDb; автоматически не обновляется
        db.executemany("INSERT INTO films VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "Интерстеллар", 2014, "Фантастика", 169, 8.7, 1),
            (2, "Начало", 2010, "Фантастика", 148, 8.8, 1),
            (3, "Титаник", 1997, "Драма", 194, 8.0, 2),
            (4, "Аватар", 2009, "Фантастика", 162, 7.9, 2),
            (5, "Назад в будущее", 1985, "Фантастика", 116, 8.5, 3),
            (6, "Форрест Гамп", 1994, "Драма", 142, 8.8, 3),
            (7, "Парк юрского периода", 1993, "Приключения", 127, 8.2, 4),
            (8, "Список Шиндлера", 1993, "Драма", 196, 9.0, 4),
            (9, "Унесённые призраками", 2001, "Анимация", 125, 8.6, 5),
            (10, "Ходячий замок", 2004, "Анимация", 119, 8.2, 5),
            (11, "Криминальное чтиво", 1994, "Криминал", 154, 8.8, 6),
            (12, "Джанго освобождённый", 2012, "Вестерн", 165, 8.5, 6),
        ])
    return path


if __name__ == "__main__":
    print(create_demo(Path(__file__).with_name("cinema.db")))
