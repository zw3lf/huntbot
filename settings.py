import os
from typing import List, Dict

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DiscordTarget(BaseModel):
    webhook_url: str
    roles: Dict[str, str]



class RawSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get('DOTENV_FILE', '.env'),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='allow'
    )
    targets: Dict[str, DiscordTarget]
