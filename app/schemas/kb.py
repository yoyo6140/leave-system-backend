from datetime import datetime
from pydantic import BaseModel


class KbDocumentOut(BaseModel):
    id:            str
    title:         str
    source:        str
    type:          str
    status:        str
    error_message: str | None = None
    uploaded_by:   int
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


class KbDocumentListData(BaseModel):
    total: int
    page:  int
    limit: int
    data:  list[KbDocumentOut]


class KbDocumentListResponse(BaseModel):
    success: bool = True
    data: KbDocumentListData


class KbDocumentResponse(BaseModel):
    success: bool = True
    data: KbDocumentOut


class KbDocumentDetail(KbDocumentOut):
    content: str


class KbDocumentDetailResponse(BaseModel):
    success: bool = True
    data: KbDocumentDetail

class KbDocumentCreate(BaseModel):
    title:   str
    content: str
    type:    str  = "rule"

class KbDocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    type:    str | None = None