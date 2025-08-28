from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

class GraphInput(BaseModel):
    id: str
    name: str
    from_time: str
    to_time: str

class HostInput(BaseModel):
    id: str
    name: str
    graphs: List[GraphInput]

class HostgroupInput(BaseModel):
    id: str
    name: str

class ReportRequest(BaseModel):
    hostgroup: HostgroupInput
    hosts: List[HostInput]
    summary: Optional[Dict[str, Any]] = None
    logo_filename: Optional[str] = None
    analyst: Optional[str] = None
    comments: Optional[str] = None
    frequency: Optional[str] = None
    summaryOptions: Optional[Dict[str, Any]] = None
    itsm: Optional[Dict[str, Any]] = None
    glpi: Optional[Dict[str, Any]] = None
