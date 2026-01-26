from fastapi import APIRouter

from app.models.schemas import SimulateRequest, SimulateResponse
from app.services.simulate import simulate_from_reactflow

router = APIRouter()


@router.post("/api/v1/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return simulate_from_reactflow(req)

