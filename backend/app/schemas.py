from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AreaExportRequest(BaseModel):
    row0: Optional[float] = None
    col0: Optional[float] = None
    height: Optional[float] = None
    width: Optional[float] = None

    polygon: Optional[List[Dict[str, Any]]] = None

    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
