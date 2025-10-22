"""
Proposal model.
Represents AI-generated technical proposals for projects.
"""

from sqlalchemy import Column, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Proposal(BaseModel):
    """
    Proposal model representing an AI-generated technical proposal.
    
    Stores proposal metadata, content, and generated artifacts (charts, PDFs).
    Uses JSON columns to store structured data from AI generation.
    
    Attributes:
        project_id: Parent project
        version: Proposal version (e.g., "v1.0", "v2.1")
        title: Proposal title
        proposal_type: Type (Conceptual, Technical, Detailed)
        status: Status (Draft, Current, Archived)
        author: Author name (usually "H2O Allegiant AI")
        capex: Capital expenditure estimate
        opex: Operational expenditure estimate
        executive_summary: Executive summary text
        technical_approach: Technical approach description
        cost_breakdown: Financial breakdown (JSON)
        implementation_plan: Implementation plan text
        risks: List of identified risks (JSON)
        equipment_list: List of equipment specifications (JSON)
        treatment_efficiency: Treatment efficiency metrics (JSON)
        operational_costs: Operational cost breakdown (JSON)
        operational_data: Operational parameters (JSON)
        charts_data: Chart data for visualization (JSON)
        pdf_path: Path to generated PDF file
    """
    
    __tablename__ = "proposals"
    
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Metadata
    version = Column(
        String(20),
        nullable=False,
        comment="Proposal version (e.g., v1.0, v2.1)",
    )
    
    title = Column(String(255), nullable=False)
    
    proposal_type = Column(
        String(50),
        nullable=False,
        comment="Conceptual, Technical, or Detailed",
    )
    
    status = Column(
        String(50),
        default="Draft",
        nullable=False,
        comment="Draft, Current, or Archived",
    )
    
    author = Column(
        String(255),
        default="H2O Allegiant AI",
        nullable=False,
    )
    
    # Financial Summary
    capex = Column(
        Float,
        default=0.0,
        comment="Capital expenditure estimate in USD",
    )
    
    opex = Column(
        Float,
        default=0.0,
        comment="Annual operational expenditure estimate in USD",
    )
    
    # Content Sections
    executive_summary = Column(Text, nullable=True)
    technical_approach = Column(Text, nullable=True)
    implementation_plan = Column(Text, nullable=True)
    
    # Structured Data (JSON from AI generation)
    cost_breakdown = Column(
        JSON,
        nullable=True,
        comment="Financial breakdown: equipment_cost, civil_works, installation_piping, etc.",
    )
    
    risks = Column(
        JSON,
        nullable=True,
        comment="List of identified risks",
    )
    
    equipment_list = Column(
        JSON,
        nullable=True,
        comment="List of EquipmentSpec objects with technical details",
    )
    
    treatment_efficiency = Column(
        JSON,
        nullable=True,
        comment="Treatment efficiency metrics: COD, BOD, TSS, TN, TP, FOG",
    )
    
    operational_costs = Column(
        JSON,
        nullable=True,
        comment="Operational cost breakdown: electrical_energy, chemicals, personnel, maintenance",
    )
    
    operational_data = Column(
        JSON,
        nullable=True,
        comment="Operational parameters: required_area_m2, sludge_production, energy_consumption",
    )
    
    # Visualizations
    charts_data = Column(
        JSON,
        nullable=True,
        comment="Chart data for visualization generation",
    )
    
    # Generated Files
    pdf_path = Column(
        String(500),
        nullable=True,
        comment="Path to generated PDF file (S3 URL or local path)",
    )
    
    # AI transparency metadata (Phase 1) ✅
    ai_metadata = Column(
        JSON,
        nullable=True,
        comment="AI reasoning metadata: usage_stats, proven_cases, deviations, assumptions, confidence_level",
    )
    
    # Relationships
    project = relationship("Project", back_populates="proposals")
    
    def __repr__(self) -> str:
        return f"<Proposal {self.version} for Project {self.project_id}>"
