# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import json

from api.models import (
    CampaignCreate, CampaignResponse, Campaign, CampaignStatus,
    AgentResponse, FindingResponse,
    WSMessage, WSMessageType
)
from api.database import get_db, init_db, close_db, CampaignDB, AgentDB, FindingDB
from api.redis_queue import redis_queue, get_redis

app = FastAPI(
    title="AI Red Team Platform",
    description="Autonomous penetration testing with persona-based AI agents",
    version="0.1.0"
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events

@app.on_event("startup")
async def startup_event():
    """Initialize database and Redis on startup"""
    await init_db()
    await redis_queue.connect()
    print("✓ API Server started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await redis_queue.disconnect()
    await close_db()
    print("✓ API Server shutdown complete")


# Health check endpoint

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-red-team-api"}


# Campaign endpoints

@app.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new penetration testing campaign"""

    # Convert Pydantic models to JSON for storage
    team_config = [member.model_dump() for member in campaign.team]
    safety_config = campaign.safety.model_dump() if campaign.safety else None

    # Create database record
    db_campaign = CampaignDB(
        name=campaign.name,
        target=campaign.target,
        mode=campaign.mode,
        team_config=team_config,
        safety_config=safety_config,
        status=CampaignStatus.PENDING
    )

    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)

    # Publish campaign created event
    await redis_queue.publish_update(
        db_campaign.id,
        WSMessage(
            type=WSMessageType.CAMPAIGN_STATUS,
            campaign_id=UUID(db_campaign.id),
            data={
                "status": CampaignStatus.PENDING,
                "message": f"Campaign '{campaign.name}' created"
            }
        )
    )

    return CampaignResponse(
        id=UUID(db_campaign.id),
        name=db_campaign.name,
        target=db_campaign.target,
        status=db_campaign.status,
        mode=db_campaign.mode,
        created_at=db_campaign.created_at,
        started_at=db_campaign.started_at,
        completed_at=db_campaign.completed_at
    )


@app.post("/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Start a campaign (begins agent orchestration)"""
    from api.orchestrator import orchestrator

    # Verify campaign exists
    result = await db.execute(
        select(CampaignDB).where(CampaignDB.id == str(campaign_id))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Campaign already {campaign.status}")

    # Start the campaign orchestrator
    await orchestrator.start_campaign(str(campaign_id))

    return {"status": "started", "campaign_id": str(campaign_id)}


@app.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get campaign status and details"""

    result = await db.execute(
        select(CampaignDB).where(CampaignDB.id == str(campaign_id))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        id=UUID(campaign.id),
        name=campaign.name,
        target=campaign.target,
        status=campaign.status,
        mode=campaign.mode,
        created_at=campaign.created_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at
    )


@app.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns"""

    result = await db.execute(
        select(CampaignDB).offset(skip).limit(limit)
    )
    campaigns = result.scalars().all()

    return [
        CampaignResponse(
            id=UUID(c.id),
            name=c.name,
            target=c.target,
            status=c.status,
            mode=c.mode,
            created_at=c.created_at,
            started_at=c.started_at,
            completed_at=c.completed_at
        )
        for c in campaigns
    ]


# Agent endpoints

@app.get("/campaigns/{campaign_id}/agents", response_model=List[AgentResponse])
async def list_campaign_agents(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all agents for a campaign"""

    result = await db.execute(
        select(AgentDB).where(AgentDB.campaign_id == str(campaign_id))
    )
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=UUID(a.id),
            campaign_id=UUID(a.campaign_id),
            persona=a.persona,
            status=a.status,
            created_at=a.created_at,
            tasks_completed=a.tasks_completed
        )
        for a in agents
    ]


@app.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all agents"""

    result = await db.execute(
        select(AgentDB).offset(skip).limit(limit)
    )
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=UUID(a.id),
            campaign_id=UUID(a.campaign_id),
            persona=a.persona,
            status=a.status,
            created_at=a.created_at,
            tasks_completed=a.tasks_completed
        )
        for a in agents
    ]


# Finding endpoints

@app.get("/campaigns/{campaign_id}/findings", response_model=List[FindingResponse])
async def list_campaign_findings(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all findings for a campaign"""

    result = await db.execute(
        select(FindingDB).where(FindingDB.campaign_id == str(campaign_id))
    )
    findings = result.scalars().all()

    return [
        FindingResponse(
            id=UUID(f.id),
            campaign_id=UUID(f.campaign_id),
            agent_id=UUID(f.agent_id),
            title=f.title,
            description=f.description,
            severity=f.severity,
            target_host=f.target_host,
            target_port=f.target_port,
            discovered_at=f.discovered_at
        )
        for f in findings
    ]


@app.get("/findings", response_model=List[FindingResponse])
async def list_findings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all findings"""

    result = await db.execute(
        select(FindingDB).offset(skip).limit(limit)
    )
    findings = result.scalars().all()

    return [
        FindingResponse(
            id=UUID(f.id),
            campaign_id=UUID(f.campaign_id),
            agent_id=UUID(f.agent_id),
            title=f.title,
            description=f.description,
            severity=f.severity,
            target_host=f.target_host,
            target_port=f.target_port,
            discovered_at=f.discovered_at
        )
        for f in findings
    ]


# WebSocket endpoint for live updates

@app.websocket("/campaigns/{campaign_id}/ws")
async def campaign_websocket(
    websocket: WebSocket,
    campaign_id: UUID
):
    """WebSocket endpoint for real-time campaign updates"""

    await websocket.accept()

    # Subscribe to campaign updates
    pubsub = await redis_queue.subscribe_to_campaign(str(campaign_id))

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "campaign_id": str(campaign_id),
            "message": "Connected to campaign updates"
        })

        # Listen for updates and forward to WebSocket
        async for message in pubsub.listen():
            if message["type"] == "message":
                # Forward Redis pub/sub message to WebSocket
                await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for campaign {campaign_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup
        await redis_queue.unsubscribe_from_campaign(pubsub, str(campaign_id))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
