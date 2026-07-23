from typing import Optional

from pydantic import BaseModel


class Attachment(BaseModel):
    type: str
    filename: str
    content: str
    mime_type: Optional[str] = None


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    use_rag: Optional[bool] = True
    use_web_search: Optional[bool] = False
    attachments: Optional[list[Attachment]] = None
