from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.database import get_db, AsyncSessionLocal
from app.models import User, Case, Message, CaseStatus, Role
from app.core.security import decode_access_token
from app.schemas import MessageResponse, MessageCreate
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, case_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if case_id not in self.active_connections:
            self.active_connections[case_id] = {}
        self.active_connections[case_id][user_id] = websocket

    def disconnect(self, case_id: str, user_id: str):
        if case_id in self.active_connections:
            self.active_connections[case_id].pop(user_id, None)

    async def send_to_user(self, case_id: str, user_id: str, data: dict):
        """특정 유저에게만 메시지 전송 (비공개)"""
        connections = self.active_connections.get(case_id, {})
        ws = connections.get(user_id)
        if ws:
            await ws.send_json(data)

    async def broadcast_verdict(self, case_id: str, data: dict):
        """판결은 양측 모두에게 전송"""
        for ws in self.active_connections.get(case_id, {}).values():
            await ws.send_json(data)


manager = ConnectionManager()


@router.websocket("/{case_id}")
async def websocket_chat(case_id: str, websocket: WebSocket, token: str):
    """
    WebSocket 채팅 엔드포인트
    연결: ws://host/chat/{case_id}?token=JWT토큰
    """
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload.get("sub")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()

        if not case or user_id not in [case.plaintiff_id, case.defendant_id]:
            await websocket.close(code=4003)
            return

        role = Role.PLAINTIFF if user_id == case.plaintiff_id else Role.DEFENDANT
        await manager.connect(case_id, user_id, websocket)

        # 기존 메시지 로드 (본인 것만)
        result = await db.execute(
            select(Message).where(
                Message.case_id == case_id,
                Message.user_id == user_id,
            ).order_by(Message.created_at)
        )
        past_messages = result.scalars().all()
        for msg in past_messages:
            await manager.send_to_user(case_id, user_id, {
                "type": "message",
                "id": msg.id,
                "content": msg.content,
                "role": msg.role.value,
                "created_at": msg.created_at.isoformat(),
            })

    try:
        while True:
            data = await websocket.receive_text()
            payload_data = json.loads(data)
            content = payload_data.get("content", "").strip()

            if not content:
                continue

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Case).where(Case.id == case_id))
                case = result.scalar_one_or_none()

                if case.status == CaseStatus.JUDGED:
                    await manager.send_to_user(case_id, user_id, {
                        "type": "error",
                        "message": "이미 판결이 완료된 사건입니다",
                    })
                    continue

                # -- 자동화: 욕설/비방 AI 필터링 --
                from app.services.moderation import check_moderation
                mod = await check_moderation(content)
                if mod["is_blocked"]:
                    await manager.send_to_user(case_id, user_id, {
                        "type": "blocked",
                        "reason": mod["reason"],
                        "suggestion": mod["cleaned"],
                    })
                    continue

                # 메시지 저장
                message = Message(
                    case_id=case_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                )
                db.add(message)
                await db.commit()

    except WebSocketDisconnect:
        manager.disconnect(case_id, user_id)


@router.get("/{case_id}/messages", response_model=list[MessageResponse])
async def get_my_messages(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """본인 메시지 조회"""
    result = await db.execute(
        select(Message)
        .where(Message.case_id == case_id, Message.user_id == current_user.id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{case_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    case_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """메시지 전송"""
    from app.schemas import MessageCreate as MC

    from fastapi import HTTPException
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다")
    if current_user.id not in [case.plaintiff_id, case.defendant_id]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
    if case.status == CaseStatus.JUDGED:
        raise HTTPException(status_code=400, detail="이미 판결이 완료된 사건입니다")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="메시지를 입력해주세요")

    from app.services.moderation import check_moderation
    mod = await check_moderation(content)
    if mod["is_blocked"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=mod["reason"])

    role = Role.PLAINTIFF if current_user.id == case.plaintiff_id else Role.DEFENDANT
    message = Message(case_id=case_id, user_id=current_user.id, role=role, content=content)
    db.add(message)
    await db.flush()
    return message
