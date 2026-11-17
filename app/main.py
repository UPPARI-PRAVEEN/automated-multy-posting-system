from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService, create_posting_service

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description="Publish a validated message to configured social platforms.",
    version="1.0.0",
)


def get_posting_service(
    settings: Settings = Depends(get_settings),
) -> PostingService:
    return create_posting_service(settings)


@app.post("/posting", response_model=PostingResponse)
async def posting(
    request: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    return await service.post(request.message)
