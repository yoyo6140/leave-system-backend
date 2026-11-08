from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, User
from app.schemas import KbDocumentOut, KbDocumentCreate, KbDocumentListResponse, KbDocumentResponse, MessageResponse, ok, fail
from app.auth import get_current_user
from app.routers.users import require_admin

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get(
    "/documents",
    status_code=status.HTTP_200_OK,
    summary="查詢規章列表",
    description="所有角色可查看",
    response_model=KbDocumentListResponse,
)
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(KbDocument).order_by(KbDocument.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return ok({
        "total": total,
        "page": page,
        "limit": limit,
        "data": [KbDocumentOut.model_validate(d) for d in items],
    })


@router.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
    summary="新增規章",
    description="admin 限定，直接貼上文字內容，新增後狀態為 processing，背景任務自動切段、向量化",
    response_model=KbDocumentResponse,
)
def create_document(
    body: KbDocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if not body.content.strip():
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("EMPTY_CONTENT", "內容不可為空"))

    document = KbDocument(
        title=body.title,
        source="manual",
        status="processing",
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # TODO: background_tasks.add_task(process_document, document.id, body.content)
    # process_document：切段（app/ai/ingest.py）→ 呼叫 embedding API → 寫入 kb_chunks，
    # 成功時 status 改 ready，失敗時改 failed + error_message

    return ok(KbDocumentOut.model_validate(document))



@router.delete(
    "/documents/{id}",
    status_code=status.HTTP_200_OK,
    summary="刪除規章",
    description="admin 限定，連同底下所有段落一起刪除",
    response_model=MessageResponse,
)
def delete_document(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    document = db.query(KbDocument).filter(KbDocument.id == id).first()
    if not document:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("NOT_FOUND", "找不到此規章文件"))

    db.delete(document)
    db.commit()
    return ok({"message": "規章已刪除"})