"""
Project model.
Represents water treatment engineering projects.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Project(BaseModel):
    """
    Project model representing a water treatment engineering project.
    
    This model matches the frontend ProjectSummary/ProjectDetail interfaces.
    
    Attributes:
        user_id: Owner of the project
        name: Project name
        client: Client company/organization name
        sector: Industry sector (Municipal, Industrial, Commercial, Residential)
        subsector: Industry subsector
        location: Project location
        project_type: Type of water treatment system
        description: Project description
        budget: Estimated budget in USD
        schedule_summary: Schedule summary text
        status: Current project status
        progress: Project completion percentage (0-100)
        tags: Optional tags for categorization
    """
    
    __tablename__ = "projects"
    
    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    client = Column(String(255), nullable=False)
    sector = Column(
        String(100),
        nullable=False,
        comment="Municipal, Industrial, Commercial, Residential",
    )
    subsector = Column(String(100), nullable=True)
    location = Column(String(255), nullable=False)
    project_type = Column(
        String(100),
        default="Por definir",
        comment="Type of treatment system",
    )
    description = Column(Text, nullable=True)
    
    # Financial
    budget = Column(Float, default=0.0, comment="Estimated budget in USD")
    
    # Schedule
    schedule_summary = Column(
        String(255),
        default="Por definir",
        comment="High-level schedule summary",
    )
    
    # Status and Progress
    status = Column(
        String(50),
        default="In Preparation",
        nullable=False,
        index=True,
        comment="Project status matching frontend enum",
    )
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Completion percentage 0-100",
    )
    
    # Metadata
    tags = Column(
        JSON,
        default=list,
        comment="Array of tags for categorization",
    )
    
    # ═══════════════════════════════════════════════════════════
    # FLEXIBLE PROJECT DATA (JSONB)
    # ═══════════════════════════════════════════════════════════
    project_data = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default='{}',
        comment="Flexible JSONB storage for all project technical data"
    )
    
    # Index for JSONB queries
    __table_args__ = (
        Index('ix_project_data_gin', 'project_data', postgresql_using='gin'),
    )
    
    # Relationships
    user = relationship("User", back_populates="projects")
    
    proposals = relationship(
        "Proposal",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(Proposal.created_at)",
        lazy="selectin",  # ✅ Load proposals eagerly with project
    )
    
    files = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(ProjectFile.created_at)",
        lazy="dynamic",
    )
    
    timeline = relationship(
        "TimelineEvent",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(TimelineEvent.created_at)",
        lazy="selectin",  # Eager load for timeline (limited in serializer)
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.name}>"

    @property
    def proposals_count(self) -> int:
        """Count of proposals for this project."""
        return len(self.proposals) if self.proposals else 0
