from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, SecretStr
from .cloud_ocr import CloudError


class ProviderConfig(BaseModel):
    endpoint: str = Field(max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    key: SecretStr
    remember: bool = False


def install_control(app, settings, cloud):
    if not settings.desktop_token:
        return

    @app.put("/internal/desktop/config", include_in_schema=False)
    def configure(body: ProviderConfig):
        try:
            return cloud.configure({"endpoint": body.endpoint, "model": body.model,
                                    "key": body.key.get_secret_value()})
        except CloudError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.delete("/internal/desktop/config", include_in_schema=False)
    def clear():
        return cloud.configure(None)
