from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.trial_ws import trial_manager
from app.core.security import decode_access_token

router = APIRouter(tags=["Trial Progress"])


@router.websocket("/ws/trial/{case_id}")
async def trial_progress_ws(case_id: str, websocket: WebSocket, token: str = ""):
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    await trial_manager.connect(case_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # 연결 유지용, 수신 무시
    except WebSocketDisconnect:
        trial_manager.disconnect(case_id, websocket)
