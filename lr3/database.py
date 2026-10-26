from pathlib import Path
from uuid import uuid4
import re

from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel


class DatabaseError(Exception):
    pass


def quote_identifier(name):
    """Кавычки нужны и для таблиц с пробелами или кавычками в имени."""
    return '"' + name.replace('"', '""') + '"'


def open_database(filename):
    """Возвращает имя проверенного соединения, не сохраняя копию QSqlDatabase."""
    path = Path(filename).resolve()
    if not path.is_file():
        raise DatabaseError("Файл базы данных не найден.")
    if not QSqlDatabase.isDriverAvailable("QSQLITE"):
        raise DatabaseError("Драйвер QSQLITE недоступен. Переустанови PyQt5.")
    name = "cinema_" + uuid4().hex
    db = QSqlDatabase.addDatabase("QSQLITE", name)
    db.setDatabaseName(str(path))
    db.setConnectOptions("QSQLITE_OPEN_READONLY;QSQLITE_BUSY_TIMEOUT=3000")
    error = ""
    if not db.open():
        error = db.lastError().text()
    else:
        # open() сам по себе ещё не подтверждает, что файл содержит SQLite
        probe = QSqlQuery(db)
        if not probe.exec_("SELECT * FROM sqlite_master LIMIT 1"):
            error = probe.lastError().text()
        probe.finish()
        del probe
    if error:
        db.close()
        db = QSqlDatabase()
        QSqlDatabase.removeDatabase(name)
        raise DatabaseError("Не удалось открыть SQLite-базу:\n" + error)
    return name


def close_database(name):
    """Вызывать только после clear() всех моделей этого соединения."""
    if name and QSqlDatabase.contains(name):
        QSqlDatabase.database(name, open=False).close()
        QSqlDatabase.removeDatabase(name)


def user_tables(name):
    query = QSqlQuery(QSqlDatabase.database(name, open=False))
    if not query.exec_(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ):
        error = query.lastError().text()
        query.finish()
        del query
        raise DatabaseError(error)
    names = []
    while query.next():
        names.append(query.value(0))
    query.finish()
    return names


class ResultModel(QSqlQueryModel):
    """QSqlQueryModel с подсказкой для длинного содержимого ячеек."""
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.ToolTipRole:
            value = super().data(index, Qt.DisplayRole)
            return "" if value is None else str(value)
        return super().data(index, role)


def make_query_model(sql, connection_name, parent=None):
    if not connection_name or not QSqlDatabase.contains(connection_name):
        raise DatabaseError("Сначала установи соединение с базой данных.")
    if not QSqlDatabase.database(connection_name, open=False).isOpen():
        raise DatabaseError("Соединение с базой данных закрыто.")
    model = ResultModel(parent)
    model.setQuery(sql, QSqlDatabase.database(connection_name, open=False))
    if model.lastError().isValid():
        error = model.lastError().text()
        model.clear()
        model.deleteLater()
        raise DatabaseError(error)
    if not model.query().isSelect():
        model.clear()
        model.deleteLater()
        raise DatabaseError("Нужен запрос на выборку данных — SELECT или WITH … SELECT.")
    return model


def validate_custom_query(sql):
    sql = sql.strip()
    if not sql:
        raise DatabaseError("Введи SQL-запрос.")
    # Пропускаем комментарии перед первым ключевым словом
    beginning = re.sub(r"\A(?:\s+|--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/)*", "", sql)
    if not re.match(r"(?:SELECT|WITH)\b", beginning, re.IGNORECASE):
        raise DatabaseError("Здесь выполняются запросы SELECT или WITH … SELECT. База открыта для чтения.")
    return sql
