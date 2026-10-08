# Extracted without method-body edits from Mooncake; see provenance.json and NOTICE.
import json
import logging
from aiohttp import web

async def handle_get(self, request):
    try:
        key = request.match_info["key"]
        exists = self.store.is_exist(key)

        if exists == 0:
            return web.Response(
                status=404,
                text=json.dumps({"error": "Key not found"}),
                content_type="application/json",
            )
        if exists < 0:
            return web.Response(
                status=500,
                text=json.dumps({"error": "Exist check failed"}),
                content_type="application/json",
            )

        value = self.store.get(key)
        if value is None:
            return web.Response(
                status=500,
                text=json.dumps({"error": "GET operation failed"}),
                content_type="application/json",
            )
        if value == b"":
            exists = self.store.is_exist(key)
            if exists == 0:
                return web.Response(
                    status=404,
                    text=json.dumps({"error": "Key not found"}),
                    content_type="application/json",
                )
            if exists < 0:
                return web.Response(
                    status=500,
                    text=json.dumps({"error": "Exist check failed"}),
                    content_type="application/json",
                )

        return web.Response(
            status=200, body=value, content_type="application/octet-stream"
        )
    except Exception as e:
        logging.error("GET error: %s", e)
        return web.Response(
            status=500,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )
