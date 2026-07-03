from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    use_rag: Optional[bool] = True
    use_web_search: Optional[bool] = False
