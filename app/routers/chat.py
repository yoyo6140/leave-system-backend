import os

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/chat", tags=["chat"])

_SYSTEM_PROMPT = """你是請假管理系統的 AI 助理，使用繁體中文回覆，語氣專業且友善。
你熟悉以下內容：
- 系統假別：特休、病假、事假、婚假、喪假、公假、其他
- 台灣勞基法第 38 條（特別休假）規定
- 請假申請、審核、取消流程
- 假別餘額與計算方式（以到職週年度為基準）
若問題超出請假範疇，禮貌說明你主要協助請假相關問題。"""


class ChatMessage(BaseModel):
    role:    str   # "user" | "model"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="AI 對話",
    description="以 Gemini 進行多輪對話，需登入。送入完整對話歷史，回傳 AI 回覆。",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "AI 回覆",
            "content": {"application/json": {"example": {"reply": "特休假依勞基法第 38 條規定…"}}},
        },
        503: {"description": "GEMINI_API_KEY 未設定"},
    },
)
def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY 未設定，請聯繫管理員",
        )

    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="訊息不可為空",
        )

    # 最後一則必須是 user
    if body.messages[-1].role != "user":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="最後一則訊息必須來自 user",
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=_SYSTEM_PROMPT,
        )

        # history = 所有訊息（不含最後一則）
        history = [
            {"role": m.role, "parts": [{"text": m.content}]}
            for m in body.messages[:-1]
        ]
        user_input = body.messages[-1].content

        session  = model.start_chat(history=history)
        response = session.send_message(user_input)

        return ChatResponse(reply=response.text)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 服務錯誤：{e}",
        )
