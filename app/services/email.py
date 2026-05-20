from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings


def _get_mail_client() -> FastMail | None:
    """이메일 설정이 있을 때만 FastMail 인스턴스 반환"""
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        return None
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )
    return FastMail(conf)


async def send_verdict_email(
    to_email: str,
    nickname: str,
    case_title: str,
    role: str,
    my_ratio: int,
    opponent_ratio: int,
    judgment: str,
    missions: list[str],
):
    fm = _get_mail_client()
    if fm is None:
        return  # 이메일 설정 없으면 스킵

    role_label = "원고" if role == "plaintiff" else "피고"
    winner = "승소" if my_ratio < opponent_ratio else ("패소" if my_ratio > opponent_ratio else "무승부")
    missions_html = "".join(f"<li>✅ {m}</li>" for m in missions)

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 24px;">
        <h2 style="color: #333;">⚖️ 커플 재판소 판결 결과</h2>
        <p>안녕하세요, <strong>{nickname}</strong>님 ({role_label})</p>
        <p>사건 <strong>"{case_title}"</strong>의 판결이 완료되었습니다.</p>

        <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <h3>📊 잘못 비율</h3>
            <p>내 잘못: <strong>{my_ratio}%</strong> | 상대방 잘못: <strong>{opponent_ratio}%</strong></p>
            <p style="font-size: 20px;">결과: <strong>{winner}</strong></p>
        </div>

        <div style="margin: 16px 0;">
            <h3>📜 판결문</h3>
            <p style="line-height: 1.8;">{judgment}</p>
        </div>

        <div style="background: #fff3cd; padding: 16px; border-radius: 8px;">
            <h3>💝 화해 미션</h3>
            <ul>{missions_html}</ul>
        </div>

        <p style="color: #999; font-size: 12px; margin-top: 24px;">
            커플 재판소 | 사랑싸움도 공정하게
        </p>
    </div>
    """

    message = MessageSchema(
        subject=f"⚖️ [{case_title}] 판결 결과가 나왔습니다",
        recipients=[to_email],
        body=html_body,
        subtype="html",
    )

    await fm.send_message(message)


async def send_verdict_to_both(
    plaintiff_email: str,
    plaintiff_nickname: str,
    defendant_email: str,
    defendant_nickname: str,
    case_title: str,
    plaintiff_ratio: int,
    defendant_ratio: int,
    judgment: str,
    missions: list[str],
):
    await send_verdict_email(
        to_email=plaintiff_email,
        nickname=plaintiff_nickname,
        case_title=case_title,
        role="plaintiff",
        my_ratio=plaintiff_ratio,
        opponent_ratio=defendant_ratio,
        judgment=judgment,
        missions=missions,
    )
    await send_verdict_email(
        to_email=defendant_email,
        nickname=defendant_nickname,
        case_title=case_title,
        role="defendant",
        my_ratio=defendant_ratio,
        opponent_ratio=plaintiff_ratio,
        judgment=judgment,
        missions=missions,
    )
