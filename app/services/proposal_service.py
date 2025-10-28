"""
Proposal service for generating technical proposals using AI.
Handles proposal generation workflow and job management.
"""

import asyncio
import logging
import structlog
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import time

# Retry logic for transient failures
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

# OpenAI exception types for retry logic
try:
    from openai import (
        APIError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
    )
except ImportError:
    # Fallback for older openai versions
    APIError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception
    APIConnectionError = Exception

from app.core.config import settings
from app.models.project import Project
from app.models.proposal import Proposal
from app.models.project_input import FlexibleWaterProjectData
from app.schemas.proposal import ProposalGenerationRequest
from app.services.cache_service import cache_service
from app.agents.proposal_agent import (
    generate_enhanced_proposal,
    ProposalGenerationError,
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# RETRY WRAPPER FOR AI GENERATION
# ═══════════════════════════════════════════════════════════════════
# Retry only on transient errors (OpenAI rate limits, timeouts, network)
# Do NOT retry on permanent errors (validation, schema, business logic)
# ═══════════════════════════════════════════════════════════════════

@retry(
    # Stop after 2 attempts (1 retry)
    stop=stop_after_attempt(2),
    
    # Exponential backoff: wait 4s, 8s, 10s (max)
    wait=wait_exponential(
        multiplier=1,
        min=4,
        max=10
    ),
    
    # Only retry on transient OpenAI errors and timeouts
    retry=retry_if_exception_type((
        APIError,           # OpenAI server errors (5xx)
        RateLimitError,     # Rate limit exceeded (429)
        APITimeoutError,    # Request timeout
        APIConnectionError, # Network connection issues
        asyncio.TimeoutError, # Our custom timeout
    )),
    
    # Log retry attempts for monitoring
    before_sleep=before_sleep_log(logger, logging.WARNING),
    
    # Re-raise exception after all retries exhausted
    reraise=True,
)
async def _generate_with_retry(
    water_data: FlexibleWaterProjectData,
    client_metadata: dict,
    job_id: str,
) -> Any:
    """
    Generate proposal with automatic retry on transient failures.
    
    This wrapper function provides resilience against:
    - OpenAI rate limits (429)
    - OpenAI server errors (5xx)
    - Network timeouts
    - Connection issues
    
    Permanent errors (validation, schema) are NOT retried and fail immediately.
    
    Args:
        water_data: Project technical data
        client_metadata: Client and project metadata
        job_id: Unique job identifier for tracking
    
    Returns:
        ProposalOutput from AI agent
        
    Raises:
        ProposalGenerationError: After all retries exhausted
        ValidationError: Immediate failure (no retry)
    """
    logger.info(f"🤖 Attempting proposal generation for job {job_id}")
    
    try:
        # Add timeout to AI agent call (fail fast - 8 minutes)
        proposal_output = await asyncio.wait_for(
            generate_enhanced_proposal(
                water_data=water_data,
                client_metadata=client_metadata,
            ),
            timeout=480  # 8 minutes (fail before frontend 10min timeout)
        )
        
        logger.info(f"✅ Proposal generated successfully for job {job_id}")
        return proposal_output
        
    except asyncio.TimeoutError:
        logger.error(f"❌ AI agent timeout after 480s for job {job_id}")
        raise ProposalGenerationError(
            "AI generation took too long (>8 min). "
            "This may indicate a loop or very complex project. "
            "Please try again or simplify requirements."
        )
    except Exception as e:
        logger.warning(f"⚠️ Proposal generation attempt failed for job {job_id}: {e}")
        raise  # Re-raise for tenacity to handle


class ProposalService:
    """Service for managing proposal generation."""
    
    @staticmethod
    def _serialize_technical_data(project: Project) -> FlexibleWaterProjectData:
        """
        Serialize project technical data for AI agent consumption.
        
        Loads from project.project_data (JSONB) which contains user's dynamic data.
        This ensures the AI agent receives the EXACT data the user entered,
        including custom contaminants, regulations, and field notes.
        
        Args:
            project: SQLAlchemy Project instance
            
        Returns:
            FlexibleWaterProjectData instance with user's dynamic data
            
        Example:
            >>> project = await db.get(Project, project_id)
            >>> water_data = ProposalService._serialize_technical_data(project)
            >>> print(water_data.count_filled_fields())  # All user fields
        """
        # Load from JSONB data (frontend's dynamic structure)
        jsonb_sections = project.project_data.get('technical_sections') if project.project_data else None
        
        if jsonb_sections:
            # ✅ User has entered dynamic data in frontend
            logger.info(
                "loading_jsonb_technical_data",
                project_id=str(project.id),
                sections_count=len(jsonb_sections),
                source="jsonb"
            )
            try:
                water_data = FlexibleWaterProjectData.from_project_jsonb(project)
                logger.info(
                    "technical_data_loaded",
                    project_id=str(project.id),
                    filled_fields=water_data.count_filled_fields(),
                    total_fields=water_data.count_fields(),
                    completeness_percent=round(water_data.count_filled_fields() / water_data.count_fields() * 100, 1)
                )
                return water_data
            except Exception as e:
                logger.error(
                    "jsonb_parsing_error",
                    exc_info=True,
                    project_id=str(project.id),
                    error_type=type(e).__name__
                )
                # Fall through to minimal structure
        
        # No technical data exists - return minimal structure
        logger.warning(
            "no_technical_data_found",
            project_id=str(project.id),
            source="none",
            action="returning_minimal_structure"
        )
        return FlexibleWaterProjectData(
            project_name=project.name,
            client=project.client,
            sector=project.sector,
            location=project.location,
            budget=project.budget,
            technical_sections=[],  # Empty
        )
    
    @staticmethod
    async def start_proposal_generation(
        db: AsyncSession,
        project_id: uuid.UUID,
        request: ProposalGenerationRequest,
        user_id: uuid.UUID,
    ) -> str:
        """
        Start a proposal generation job.
        Returns job ID for status polling.
        
        Args:
            db: Database session
            project_id: Project UUID
            request: Proposal generation request
            user_id: User UUID
            
        Returns:
            Job ID string
        """
        # Generate job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Set initial job status
        await cache_service.set_job_status(
            job_id=job_id,
            status="queued",
            progress=0,
            current_step="Initializing proposal generation...",
            ttl=3600,  # 1 hour
        )
        
        logger.info(
            "proposal_job_started",
            job_id=job_id,
            project_id=str(project_id),
            proposal_type=request.proposal_type,
            user_id=str(user_id)
        )
        
        # Note: In production, you would trigger a background task here
        # For now, we'll store the job info and it should be processed by a worker
        # TODO: Implement Celery or FastAPI BackgroundTasks
        
        return job_id
    
    @staticmethod
    async def generate_proposal_async(
        db: AsyncSession,
        project_id: uuid.UUID,
        request: ProposalGenerationRequest,
        job_id: str,
        user_id: uuid.UUID,
    ) -> None:
        """
        Generate proposal asynchronously (to be called by background worker).
        
        Args:
            db: Database session
            project_id: Project UUID
            request: Proposal generation request
            job_id: Job identifier
            user_id: User UUID
        """
        try:
            # Update status
            await cache_service.set_job_status(
                job_id=job_id,
                status="processing",
                progress=10,
                current_step="Loading project data...",
            )
            
            # Load project
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            
            # Load technical data
            await cache_service.set_job_status(
                job_id=job_id,
                status="processing",
                progress=20,
                current_step="Loading technical data...",
            )
            
            # Serialize technical data from JSONB
            await cache_service.set_job_status(
                job_id=job_id,
                status="processing",
                progress=30,
                current_step="Preparing data for AI analysis...",
            )
            
            technical_data = ProposalService._serialize_technical_data(project)
            
            # ═══════════════════════════════════════════════════════════════════
            # 🔍 DETAILED LOGGING: What data is being sent to the AI agent
            # ═══════════════════════════════════════════════════════════════════
            logger.info(
                "╔══════════════════════════════════════════════════════════════╗",
            )
            logger.info(
                "║         🤖 AI AGENT INPUT DATA - DETAILED INSPECTION         ║",
            )
            logger.info(
                "╚══════════════════════════════════════════════════════════════╝",
            )
            
            # Log technical data summary
            logger.info(
                "📦 TECHNICAL DATA SUMMARY",
                project_id=str(project_id),
                job_id=job_id,
                data_source="jsonb" if project.project_data else "relational",
                total_fields=technical_data.count_fields(),
                filled_fields=technical_data.count_filled_fields(),
                completeness_percent=round(
                    technical_data.count_filled_fields() / technical_data.count_fields() * 100, 1
                ) if technical_data.count_fields() > 0 else 0,
            )
            
            # ═══════════════════════════════════════════════════════════════════
            # 🎯 CLEAN AI CONTEXT - What actually goes to the agent
            # ═══════════════════════════════════════════════════════════════════
            ai_context = technical_data.to_ai_context()
            ai_context_str = technical_data.format_ai_context_to_string(ai_context)
            
            logger.info(
                "🎯 CLEAN AI CONTEXT (no UI metadata):",
                context_keys=list(ai_context.keys()),
                sections_count=len([k for k, v in ai_context.items() if isinstance(v, dict)]),
                estimated_tokens=len(ai_context_str) // 4,  # Rough estimate: 1 token ≈ 4 chars
            )
            
            # Log the formatted string that will be injected (first 500 chars)
            logger.info(
                "📝 FORMATTED CONTEXT PREVIEW (first 500 chars):",
                preview=ai_context_str[:500] + "..." if len(ai_context_str) > 500 else ai_context_str
            )
            
            # Prepare client metadata
            client_metadata = {
                "company_name": project.client,
                "selected_sector": project.sector,
                "selected_subsector": project.subsector,
                "user_location": project.location,
                "project_name": project.name,
                "project_type": project.project_type,
            }
            
            # Add user preferences if provided
            if request.preferences:
                client_metadata["preferences"] = request.preferences
            
            # Log client metadata
            logger.info(
                "🏢 CLIENT METADATA",
                company=client_metadata.get("company_name"),
                sector=client_metadata.get("selected_sector"),
                subsector=client_metadata.get("selected_subsector"),
                location=client_metadata.get("user_location"),
                project_type=client_metadata.get("project_type"),
                has_preferences=bool(request.preferences),
                preferences=request.preferences if request.preferences else None
            )
            
            # Comparison: Full model vs Clean context
            full_json = technical_data.model_dump_json(exclude_none=True)
            logger.info(
                "💡 TOKEN REDUCTION:",
                full_serialization_chars=len(full_json),
                clean_context_chars=len(ai_context_str),
                reduction_percent=round((1 - len(ai_context_str) / len(full_json)) * 100, 1)
            )
            
            logger.info(
                "════════════════════════════════════════════════════════════════",
            )
            
            # Generate proposal with AI
            await cache_service.set_job_status(
                job_id=job_id,
                status="processing",
                progress=40,
                current_step="Generating proposal with AI (this may take 1-2 minutes)...",
            )
            
            start_time = time.time()
            try:
                proposal_output = await _generate_with_retry(
                    water_data=technical_data,
                    client_metadata=client_metadata,
                    job_id=job_id,
                )
                generation_duration = time.time() - start_time

                logger.info(
                    "ai_proposal_generated",
                    project_id=str(project_id),
                    job_id=job_id,
                    duration_seconds=round(generation_duration, 2),
                )

                # Extract proven cases from Redis cache (no more global context)
                from app.agents.proposal_agent import _get_proven_cases_cache_key
                cache_key = _get_proven_cases_cache_key(client_metadata)
                try:
                    proven_cases_data = await cache_service.get(cache_key) or {}
                except Exception as e:
                    logger.error(f"Error retrieving proven cases for proposal: {e}")
                    proven_cases_data = {}
                
            except RetryError as e:
                # All retry attempts failed
                duration = time.time() - start_time
                logger.error(
                    "proposal_generation_failed_after_retries",
                    exc_info=True,
                    project_id=str(project_id),
                    job_id=job_id,
                    duration_seconds=round(duration, 2),
                    attempts=2,
                    last_error=str(e.last_attempt.exception())
                )
                await cache_service.set_job_status(
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    current_step="Generation failed after retries",
                    error=f"Failed after 2 attempts: {str(e.last_attempt.exception())}"
                )
                return
                
            except ProposalGenerationError as e:
                # Timeout or other non-retryable error
                duration = time.time() - start_time
                logger.error(
                    "proposal_generation_failed",
                    exc_info=True,
                    project_id=str(project_id),
                    job_id=job_id,
                    duration_seconds=round(duration, 2),
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                await cache_service.set_job_status(
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    current_step="Generation failed",
                    error=str(e),
                )
                return
            
            # Create proposal record
            await cache_service.set_job_status(
                job_id=job_id,
                status="processing",
                progress=80,
                current_step="Saving proposal...",
            )
            # Get latest proposal version to determine new version
            result = await db.execute(
                select(Proposal)
                .where(Proposal.project_id == project_id)
                .order_by(Proposal.created_at.desc())
                .limit(1)
            )
            latest_proposal = result.scalar_one_or_none()
            
            if latest_proposal:
                # Parse version and increment
                version_num = float(latest_proposal.version.replace("v", ""))
                new_version = f"v{version_num + 0.1:.1f}"
            else:
                new_version = "v1.0"
            
            # Extract data from proposal output
            tech_data = proposal_output.technical_data

            # Build AI metadata for transparency
            ai_metadata = {
                "proven_cases": proven_cases_data.get("similar_cases", []),
                "user_sector": proven_cases_data.get("user_sector", client_metadata.get("selected_sector")),
                "assumptions": tech_data.assumptions,
                "alternatives": [alt.model_dump() for alt in tech_data.alternative_analysis],
                "technology_justification": [tj.model_dump() for tj in tech_data.technology_justification],
                "confidence_level": proposal_output.confidence_level,
                "recommendations": proposal_output.recommendations or [],
                "generated_at": datetime.utcnow().isoformat(),
                "generation_time_seconds": round(generation_duration, 2),
            }
            
            # Note: Proven cases are now managed in Redis cache with TTL
            logger.info(
                "ai_metadata_prepared",
                project_id=str(project_id),
                proven_cases_count=len(ai_metadata['proven_cases']),
                alternatives_count=len(ai_metadata['alternatives']),
                confidence_level=ai_metadata['confidence_level']
            )

            # ✅ Create proposal WITH ai_metadata in PostgreSQL (best practice)
            proposal = Proposal(
                project_id=project_id,
                version=new_version,
                title=f"Propuesta {request.proposal_type} - {project.name}",
                proposal_type=request.proposal_type,
                status="Draft",
                author="H2O Allegiant AI",
                capex=tech_data.capex_usd,
                opex=tech_data.annual_opex_usd,
                executive_summary=proposal_output.markdown_content[:500],
                technical_approach=proposal_output.markdown_content,  # Full markdown
                # Extract structured data from Pydantic models
                equipment_list=[eq.model_dump() for eq in tech_data.main_equipment],
                treatment_efficiency=tech_data.treatment_efficiency.model_dump() if tech_data.treatment_efficiency else None,
                cost_breakdown=tech_data.capex_breakdown.model_dump() if tech_data.capex_breakdown else None,
                operational_costs=tech_data.opex_breakdown.model_dump() if tech_data.opex_breakdown else None,
                operational_data=tech_data.operational_data.model_dump() if tech_data.operational_data else None,
                # ✅ Save AI metadata directly in PostgreSQL (persistent, queryable, backed up)
                ai_metadata=ai_metadata,
            )
            
            db.add(proposal)
            await db.commit()
            await db.refresh(proposal)
            
            logger.info(
                "proposal_saved_to_database",
                proposal_id=str(proposal.id),
                project_id=str(project_id),
                version=new_version,
                proposal_type=request.proposal_type,
                capex=tech_data.capex_usd,
                opex=tech_data.annual_opex_usd,
                has_ai_metadata=True
            )
            
            # Complete job
            await cache_service.set_job_status(
                job_id=job_id,
                status="completed",
                progress=100,
                current_step="Proposal generated successfully!",
                result={
                    "proposalId": str(proposal.id),  # ← camelCase for frontend
                    "preview": {
                        "executiveSummary": proposal.executive_summary,  # ← camelCase
                        "capex": proposal.capex,
                        "opex": proposal.opex,
                        "keyTechnologies": [],  # ← camelCase
                    },
                },
            )
            
            logger.info(
                "proposal_generation_completed",
                proposal_id=str(proposal.id),
                project_id=str(project_id),
                job_id=job_id,
                version=new_version,
                total_duration_seconds=round(time.time() - start_time, 2)
            )
        
        except Exception as e:
            logger.error(
                "proposal_generation_error",
                exc_info=True,
                project_id=str(project_id),
                job_id=job_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            await cache_service.set_job_status(
                job_id=job_id,
                status="failed",
                progress=0,
                current_step="Failed",
                error=str(e),
            )
    
    @staticmethod
    async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get proposal generation job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status data or None
        """
        return await cache_service.get_job_status(job_id)


# Global service instance
proposal_service = ProposalService()
