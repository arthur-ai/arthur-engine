import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from config.config import Config
from db_models.demo_certificate_models import DemoCertificate
from dependencies import get_db_session
from routers.route_handler import GenaiEngineRoute
from schemas.response_schemas import CertificateUploadResponse
from utils.utils import public_endpoint

demo_certificate_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)

_MAX_CERT_BYTES = 5 * 1024 * 1024  # 5 MB


@demo_certificate_routes.post(
    "/demo/certificate",
    description="Upload a demo completion certificate PNG to persistent storage.",
    tags=["Demo"],
    response_model=CertificateUploadResponse,
)
@public_endpoint
async def upload_certificate(
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db_session),
) -> CertificateUploadResponse:
    if not Config.demo_mode():
        raise HTTPException(status_code=400, detail="Demo mode is not enabled")

    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Only PNG files are accepted")

    image_bytes = await file.read()

    if len(image_bytes) > _MAX_CERT_BYTES:
        raise HTTPException(
            status_code=413, detail="Certificate image exceeds 5 MB limit"
        )

    cert = DemoCertificate(id=uuid.uuid4(), image=image_bytes)
    db_session.add(cert)
    db_session.commit()

    return CertificateUploadResponse(
        certificate_id=str(cert.id),
        certificate_url=f"/api/v2/demo/certificate/{cert.id}",
    )


@demo_certificate_routes.get(
    "/demo/certificate/{cert_id}",
    description="Retrieve a previously stored demo completion certificate PNG.",
    tags=["Demo"],
)
@public_endpoint
async def get_certificate(
    cert_id: str,
    db_session: Session = Depends(get_db_session),
) -> Response:
    if not Config.demo_mode():
        raise HTTPException(status_code=400, detail="Demo mode is not enabled")

    try:
        cert_uuid = uuid.UUID(cert_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Certificate not found")

    cert = db_session.get(DemoCertificate, cert_uuid)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    return Response(content=cert.image, media_type="image/png")
