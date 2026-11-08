from datetime import datetime
from pydantic import BaseModel


class KbDocumentOut(BaseModel):
    id:            str
    title:         str
    source:        str
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

class KbDocumentCreate(BaseModel):
    title:   str
    content: str