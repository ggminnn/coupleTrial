from fastapi import WebSocket


class TrialProgressManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, case_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(case_id, []).append(ws)

    def disconnect(self, case_id: str, ws: WebSocket):
        conns = self._connections.get(case_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, case_id: str, step: int, total: int, message: str):
        payload = {"type": "progress", "step": step, "total": total, "message": message}
        for ws in list(self._connections.get(case_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def broadcast_done(self, case_id: str):
        payload = {"type": "done", "message": "✅ 판결 완료!"}
        for ws in list(self._connections.get(case_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                pass


trial_manager = TrialProgressManager()
