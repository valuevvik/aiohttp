
from aiohttp import web
from datetime import datetime
import uuid

ads = {}

def serialize(ad):
    return {
        "id": ad["id"],
        "title": ad["title"],
        "description": ad["description"],
        "created_at": ad["created_at"].isoformat(),
        "owner": ad["owner"],
    }

async def create_ad(request):
    data = await request.json()
    if not all(k in data for k in ("title", "description", "owner")):
        return web.json_response({"error": "title, description, owner required"}, status=400)
    ad_id = str(uuid.uuid4())
    ad = {
        "id": ad_id,
        "title": data["title"],
        "description": data["description"],
        "owner": data["owner"],
        "created_at": datetime.utcnow(),
    }
    ads[ad_id] = ad
    return web.json_response(serialize(ad), status=201)

async def get_ad(request):
    ad_id = request.match_info["id"]
    ad = ads.get(ad_id)
    if not ad:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(serialize(ad))

async def update_ad(request):
    ad_id = request.match_info["id"]
    ad = ads.get(ad_id)
    if not ad:
        return web.json_response({"error": "not found"}, status=404)
    data = await request.json()
    for field in ("title", "description", "owner"):
        if field in data:
            ad[field] = data[field]
    return web.json_response(serialize(ad))

async def delete_ad(request):
    ad_id = request.match_info["id"]
    if ads.pop(ad_id, None) is None:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response({"status": "deleted"})

app = web.Application()
app.router.add_post("/ads", create_ad)
app.router.add_get("/ads/{id}", get_ad)
app.router.add_patch("/ads/{id}", update_ad)
app.router.add_put("/ads/{id}", update_ad)
app.router.add_delete("/ads/{id}", delete_ad)

if __name__ == "__main__":
    web.run_app(app, port=8080)