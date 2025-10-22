"""
Proposal schemas for AI-generated proposals.

Includes AI transparency schemas for Phase 1 (October 2025).
"""

from typing import List, Optional, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, field_serializer

from app.schemas.common import BaseSchema, to_camel_case
from app.models.proposal_output import (
    EquipmentSpec,
    TreatmentEfficiency,
    OperationalCosts,
    FinancialBreakdown
)

class ProposalGenerationRequest(BaseModel):
    """
    Schema for requesting proposal generation.
    Matches frontend GenerateProposalRequest.
    """
    
    project_id: UUID
    proposal_type: str = Field(
        ...,
        description="Conceptual, Technical, or Detailed",
    )
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="User preferences (focus_areas, constraints)",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "proposal_type": "Technical",
                "preferences": {
                    "focus_areas": ["cost-optimization", "sustainability"],
                    "constraints": {"max_area_m2": 500},
                },
            }
        }


class ProposalPreview(BaseSchema):
    """Preview data for proposal job result.
    
    Inherits from BaseSchema to accept camelCase from Redis/frontend.
    """
    
    executive_summary: str = Field(..., max_length=500)
    capex: float
    opex: float
    key_technologies: List[str] = Field(default_factory=list)


class ProposalJobResult(BaseSchema):
    """Result data when proposal generation completes.
    
    Inherits from BaseSchema to accept camelCase from Redis/frontend.
    """
    
    proposal_id: UUID
    preview: ProposalPreview


class ProposalJobStatus(BaseSchema):
    """
    Schema for proposal generation job status.
    Matches frontend GetProposalJobStatusResponse.

    Note: Inherits from BaseSchema for camelCase serialization.
    Fields like job_id, current_step serialize as jobId, currentStep.
    """

    job_id: str
    status: str = Field(
        ...,
        description="Job status: queued, processing, completed, failed",
    )
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Current processing step")
    result: Optional[ProposalJobResult] = Field(None, description="Result when completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# EquipmentSpec, TreatmentEfficiency, FinancialBreakdown, OperationalCosts
# All imported from proposal_output (lines 13-17)
# No need to redefine them here - using single source of truth


class ProposalSnapshot(BaseModel):
    """Snapshot of proposal content for frontend display."""
    
    executive_summary: str = Field(default="", alias="executiveSummary")
    technical_approach: str = Field(default="", alias="technicalApproach")
    implementation_plan: str = Field(default="", alias="implementationPlan")
    cost_breakdown: Optional[Dict[str, float]] = Field(default=None, alias="costBreakdown")
    risks: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class ProposalResponse(BaseSchema):
    """
    Schema for proposal response.
    Matches frontend ProposalVersion interface.

    Note: Inherits from BaseSchema for camelCase serialization.
    Fields like proposal_type, created_at, cost_breakdown serialize as
    proposalType, createdAt, costBreakdown.
    """

    id: UUID
    version: str
    title: str
    proposal_type: str
    status: str
    created_at: datetime
    author: str
    capex: float
    opex: float

    # Snapshot for frontend display (grouped content)
    snapshot: Optional[ProposalSnapshot] = None
    
    # Legacy fields (kept for backward compatibility)
    executive_summary: Optional[str] = None
    technical_approach: Optional[str] = None
    implementation_plan: Optional[str] = None

    # Structured data (properly typed for recursive serialization)
    cost_breakdown: Optional[FinancialBreakdown] = None
    risks: Optional[List[str]] = None
    equipment_list: Optional[List[EquipmentSpec]] = None
    treatment_efficiency: Optional[TreatmentEfficiency] = None
    operational_costs: Optional[OperationalCosts] = None
    
    # AI transparency data (Phase 1 - Oct 2025)
    # Note: Using Dict because AI metadata structure is flexible
    ai_metadata: Optional[Dict[str, Any]] = None

    # Files
    pdf_path: Optional[str] = None
    
    # ========================================================================
    # Custom serializers for JSONB fields
    # ========================================================================
    
    @field_serializer('equipment_list', when_used='json')
    def serialize_equipment_list(self, value: Optional[List], _info):
        """Convert equipment_list dicts to camelCase on serialization."""
        if not value:
            return value
        
        def convert_dict_keys(d: dict) -> dict:
            """Recursively convert snake_case keys to camelCase."""
            return {to_camel_case(k): v for k, v in d.items()}
        
        # If already EquipmentSpec instances, dump with aliases
        if value and isinstance(value[0], EquipmentSpec):
            return [eq.model_dump(by_alias=True) for eq in value]
        
        # If raw dicts from JSONB, convert keys
        return [convert_dict_keys(eq) for eq in value]
    
    @field_serializer('treatment_efficiency', when_used='json')
    def serialize_treatment_efficiency(self, value: Optional[Dict], _info):
        """Treatment efficiency keys are already uppercase (COD, BOD, etc)."""
        return value
    
    @field_serializer('operational_costs', when_used='json')
    def serialize_operational_costs(self, value: Optional[Dict], _info):
        """Convert operational_costs dict to camelCase on serialization."""
        if not value:
            return value
        
        # If already OperationalCosts instance, dump with aliases
        if isinstance(value, OperationalCosts):
            return value.model_dump(by_alias=True)
        
        # If raw dict from JSONB, convert keys
        return {to_camel_case(k): v for k, v in value.items()}

    # ========================================================================
    # Factory method
    # ========================================================================

    @classmethod
    def from_model_with_snapshot(cls, proposal):
        """
        Create ProposalResponse from SQLAlchemy model with snapshot.

        Helper method to ensure snapshot is always constructed consistently.
        """
        # Validate base fields - field_serializers will handle JSONB conversion
        response_data = cls.model_validate(proposal).model_dump(mode='json', by_alias=True)

        # ✅ Construct snapshot from proposal fields
        # Convert cost_breakdown to dict if it's a Pydantic model
        cost_breakdown = proposal.cost_breakdown
        if cost_breakdown is not None and hasattr(cost_breakdown, 'model_dump'):
            cost_breakdown_dict = cost_breakdown.model_dump()
            # Convert snake_case to camelCase for frontend
            cost_breakdown = {
                "equipmentCost": cost_breakdown_dict.get("equipment_cost"),
                "civilWorks": cost_breakdown_dict.get("civil_works"),
                "installationPiping": cost_breakdown_dict.get("installation_piping"),
                "engineeringSupervision": cost_breakdown_dict.get("engineering_supervision"),
                "contingency": cost_breakdown_dict.get("contingency")
            }
        elif cost_breakdown is None:
            cost_breakdown = {}
        
        response_data["snapshot"] = {
            "executiveSummary": proposal.executive_summary or "",
            "technicalApproach": proposal.technical_approach or "",
            "implementationPlan": proposal.implementation_plan or "",
            "costBreakdown": cost_breakdown,
            "risks": proposal.risks or []
        }

        return cls(**response_data)


# ============================================================================
# AI Transparency Schemas - Phase 1 (October 2025)
# ============================================================================

class UsageStatsResponse(BaseModel):
    """AI usage statistics for transparency."""
    
    total_tokens: int = Field(..., ge=0, description="Total tokens consumed")
    model_used: str = Field(..., description="AI model used (e.g., gpt-4o-mini)")
    cost_estimate: Optional[float] = Field(None, ge=0, description="Estimated cost in USD")
    generation_time_seconds: Optional[float] = Field(None, ge=0, description="Generation time")
    success: bool = Field(default=True, description="Whether generation succeeded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_tokens": 45234,
                "model_used": "gpt-4o-mini",
                "cost_estimate": 0.45,
                "generation_time_seconds": 28.5,
                "success": True
            }
        }


class ProvenCaseResponse(BaseModel):
    """Proven case consulted by AI during generation."""
    
    # ✅ Make fields optional to handle legacy data
    case_id: Optional[str] = Field(None, description="Unique case identifier")
    application_type: str = Field(..., description="Application type (e.g., Municipal)")
    treatment_train: str = Field(..., description="Treatment technologies sequence")
    
    # ✅ Support both flow_rate and flow_range
    flow_rate: Optional[float] = Field(None, ge=0, description="Design flow rate (m³/day)")
    flow_range: Optional[str] = Field(None, description="Flow rate range (e.g., '100-1000 m³/day')")
    
    capex_usd: Optional[float] = Field(None, ge=0, description="Capital expenditure")
    similarity_score: Optional[float] = Field(
        None, 
        ge=0, 
        le=1,
        description="Similarity to current project (0-1)"
    )
    
    @field_validator('similarity_score')
    @classmethod
    def validate_similarity(cls, v: Optional[float]) -> Optional[float]:
        """Ensure similarity score is between 0 and 1."""
        if v is not None and not (0 <= v <= 1):
            raise ValueError('Similarity score must be between 0 and 1')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "muni_sbr_uv_500",
                "application_type": "Municipal Wastewater",
                "treatment_train": "SBR + UV Disinfection",
                "flow_rate": 500,
                "flow_range": "100-1000 m³/day",
                "capex_usd": 250000,
                "similarity_score": 0.92
            }
        }


class AlternativeTechnologyResponse(BaseModel):
    """Alternative technology considered but rejected by AI."""
    
    technology: str = Field(..., description="Technology name")
    reason_rejected: str = Field(..., description="Why it was not selected")
    
    class Config:
        json_schema_extra = {
            "example": {
                "technology": "MBBR",
                "reason_rejected": "Higher footprint required for this flow rate"
            }
        }


class TechnologyJustificationResponse(BaseModel):
    """Technical justification for technology selection."""
    
    stage: str = Field(..., description="Treatment stage (Primary, Secondary, etc.)")
    technology: str = Field(..., description="Technology selected")
    justification: str = Field(..., description="Detailed reasoning")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stage": "Secondary",
                "technology": "SBR",
                "justification": "Space-efficient biological treatment with proven reliability..."
            }
        }


class AIMetadataResponse(BaseModel):
    """
    AI Transparency Metadata Response - Phase 1 (October 2025)
    
    Exposes the AI's reasoning process for validation and trust building.
    This response model ensures data integrity and provides clear API contracts.
    
    **Transparency Features:**
    - Usage stats: Token consumption, model info, costs
    - Proven cases: Similar projects consulted from database
    - Assumptions: Design assumptions made by AI
    - Alternatives: Technologies considered but rejected
    - Justifications: Stage-by-stage technical reasoning
    - Confidence level: AI's confidence in recommendations
    
    **Validation:**
    All fields are validated at runtime via Pydantic.
    Invalid data from database will raise ValidationError.
    """
    
    usage_stats: UsageStatsResponse = Field(..., description="Token usage and model info")
    proven_cases: List[ProvenCaseResponse] = Field(
        default_factory=list,
        description="Proven cases consulted during generation"
    )
    user_sector: Optional[str] = Field(None, description="User's industry sector")
    assumptions: List[str] = Field(
        default_factory=list,
        description="Design assumptions made by AI"
    )
    alternatives: List[AlternativeTechnologyResponse] = Field(
        default_factory=list,
        description="Technologies considered but rejected"
    )
    technology_justification: List[TechnologyJustificationResponse] = Field(
        default_factory=list,
        description="Justifications for each treatment stage"
    )
    confidence_level: Literal["High", "Medium", "Low"] = Field(
        ...,
        description="AI's confidence in the proposal"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Additional recommendations from AI"
    )
    generated_at: str = Field(..., description="ISO 8601 timestamp of generation")
    
    @field_validator('generated_at')
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('generated_at must be valid ISO 8601 timestamp')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "usage_stats": {
                    "total_tokens": 45234,
                    "model_used": "gpt-4o-mini",
                    "cost_estimate": 0.45,
                    "generation_time_seconds": 28.5,
                    "success": True
                },
                "proven_cases": [
                    {
                        "case_id": "muni_sbr_uv_500",
                        "application_type": "Municipal Wastewater",
                        "treatment_train": "SBR + UV Disinfection",
                        "flow_rate": 500,
                        "capex_usd": 250000,
                        "similarity_score": 0.92
                    }
                ],
                "user_sector": "Municipal",
                "assumptions": [
                    "Peak factor of 1.5x for equipment sizing",
                    "COD/BOD ratio assumed as 2.5"
                ],
                "alternatives": [
                    {
                        "technology": "MBBR",
                        "reason_rejected": "Higher footprint required"
                    }
                ],
                "technology_justification": [
                    {
                        "stage": "Secondary",
                        "technology": "SBR",
                        "justification": "Space-efficient biological treatment..."
                    }
                ],
                "confidence_level": "High",
                "recommendations": [
                    "Consider pilot testing for 3 months",
                    "Install backup power system"
                ],
                "generated_at": "2025-10-04T21:00:00.000000Z"
            }
        }
