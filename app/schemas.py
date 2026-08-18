from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        from_attributes = True


class CommandRequest(BaseModel):
    command: str


class GithubTokenRequest(BaseModel):
    token: str


class CommandResult(BaseModel):
    output: str


class ServerSummary(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    online: bool
    pid: int | None = None
    cpu_percent: float | None = None
    cpu_percent_host: float | None = None
    memory_mb: float | None = None
    players_online: int | None = None
    error: str | None = None


class SystemStats(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
