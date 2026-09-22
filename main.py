from aiohttp import web
from datetime import datetime
import uuid
import aiosqlite

DB_PATH = "ads.db"

async def init_db(app):
    """Инициализация асинхронного подключения к SQLite и создание таблицы."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    await db.commit()
    app["db"] = db

async def close_db(app):
    """Закрытие соединения с БД при остановке приложения."""
    await app["db"].close()

def serialize(ad_row):
    """Преобразование строки БД в словарь для JSON-ответа."""
    return {
        "id": ad_row["id"],
        "title": ad_row["title"],
        "description": ad_row["description"],
        "created_at": ad_row["created_at"],
        "owner": ad_row["owner"],
    }

async def create_ad(request):
    data = await request.json()
    required = ("title", "description", "owner")
    if not all(k in data for k in required):
        return web.json_response(
            {"error": "title, description, owner required"}, status=400
        )
    # Проверка на непустые значения
    for field in required:
        if not data[field] or not str(data[field]).strip():
            return web.json_response(
                {"error": f"{field} must be non-empty"}, status=400
            )

    ad_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    db = request.app["db"]
    await db.execute(
        "INSERT INTO ads (id, title, description, owner, created_at) VALUES (?, ?, ?, ?, ?)",
        (ad_id, data["title"], data["description"], data["owner"], created_at),
    )
    await db.commit()

    async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    return web.json_response(serialize(row), status=201)

async def get_ad(request):
    ad_id = request.match_info["id"]
    db = request.app["db"]
    async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(serialize(row))

async def update_ad(request):
    ad_id = request.match_info["id"]
    db = request.app["db"]

    # Проверяем существование объявления
    async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return web.json_response({"error": "not found"}, status=404)

    data = await request.json()

    # Обязательная валидация: title и description должны присутствовать и быть непустыми
    for field in ("title", "description"):
        if field not in data:
            return web.json_response(
                {"error": f"{field} is required"}, status=400
            )
        if not data[field] or not str(data[field]).strip():
            return web.json_response(
                {"error": f"{field} must be non-empty"}, status=400
            )

    # Динамически строим запрос на обновление (owner — опционально)
    fields = []
    values = []
    for field in ("title", "description", "owner"):
        if field in data:
            fields.append(f"{field} = ?")
            values.append(data[field])
    if not fields:
        return web.json_response({"error": "no fields to update"}, status=400)

    values.append(ad_id)
    query = f"UPDATE ads SET {', '.join(fields)} WHERE id = ?"
    await db.execute(query, values)
    await db.commit()

    # Возвращаем обновлённую запись
    async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    return web.json_response(serialize(row))

async def delete_ad(request):
    ad_id = request.match_info["id"]
    db = request.app["db"]

    async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return web.json_response({"error": "not found"}, status=404)

    await db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
    await db.commit()
    return web.json_response({"status": "deleted"})

app = web.Application()
app.on_startup.append(init_db)
app.on_cleanup.append(close_db)

app.router.add_post("/ads", create_ad)
app.router.add_get("/ads/{id}", get_ad)
app.router.add_patch("/ads/{id}", update_ad)
app.router.add_put("/ads/{id}", update_ad)
app.router.add_delete("/ads/{id}", delete_ad)

if __name__ == "__main__":
    web.run_app(app, port=8080)
