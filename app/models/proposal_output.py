"""
Proposal Output Models - Data that flows FROM AI agent TO user.

This module contains structured Pydantic models for AI-generated proposals:
- Equipment specifications with technical details
- Treatment efficiency metrics
- Cost breakdowns (CAPEX/OPEX)
- Design parameters and justifications

These models define what the AI agent MUST return after analyzing user input.
"""

from typing import Any, Literal

from pydantic import Field, computed_field, model_validator

from app.schemas.common import BaseSchema


class EquipmentSpec(BaseSchema):
    """Individual equipment specification with technical semantic analysis"""

    type: str = Field(description="Equipment type (e.g., Biological Reactor, Sand Filter)")
    specifications: str = Field(
        description="Complete technical specifications (materials, capacity, performance, controls)"
    )
    capacity_m3_day: float = Field(description="Capacity in m³/day")
    power_consumption_kw: float = Field(description="Power consumption in kW")
    capex_usd: float = Field(description="Capital cost in USD")
    dimensions: str = Field(description="Dimensions in L x W x H format (meters)")

    # Technical justification (no brands)
    justification: str | None = Field(
        default=None, description="Technical justification for equipment selection"
    )

    # Semantic fields for intelligent visualization
    criticality: str | None = Field(
        default="medium", description="Equipment criticality: high/medium/low"
    )
    stage: str | None = Field(
        default="secondary",
        description="Treatment stage: primary/secondary/tertiary/auxiliary",
    )
    risk_factor: float | None = Field(
        default=0.5, description="Operational risk factor: 0.0-1.0"
    )


class TreatmentParameter(BaseSchema):
    """Single water quality parameter treatment performance"""

    parameter_name: str = Field(
        description="Parameter name EXACTLY as provided by user (preserve casing)"
    )
    influent_concentration: float = Field(
        gt=0, description="Input concentration value from influentCharacteristics (REQUIRED)"
    )
    effluent_concentration: float = Field(
        ge=0, description="Expected output concentration after treatment (REQUIRED)"
    )
    removal_efficiency_percent: float = Field(
        ge=0, le=100, description="Removal efficiency percentage (0-100)"
    )
    unit: str = Field(
        default="mg/L", description="Measurement unit (inherited from input or standard)"
    )

    # Engineering context
    treatment_stage: str | None = Field(
        default=None, description="Primary removal stage: primary, secondary, tertiary, advanced"
    )


class TreatmentEfficiency(BaseSchema):
    """
    Treatment efficiency for ALL user-provided parameters.

    This model is 100% dynamic - supports any number and type of parameters
    the user defines in their input data.

    Replaces the old hardcoded TreatmentEfficiency (BOD/COD/TSS only).

    Example:
        >>> efficiency = TreatmentEfficiency(
        ...     parameters=[
        ...         {"parameter_name": "BOD", "removal_efficiency_percent": 99},
        ...         {"parameter_name": "Chromium VI", "removal_efficiency_percent": 98}
        ...     ]
        ... )
    """

    parameters: list[TreatmentParameter] = Field(
        description="Treatment performance for each water quality parameter from user input"
    )

    overall_compliance: bool = Field(
        default=True, description="All parameters meet regulatory requirements"
    )
    critical_parameters: list[str] | None = Field(
        default=None, description="Parameters requiring special attention or close monitoring"
    )


class FinancialBreakdown(BaseSchema):
    """Basic financial breakdown"""

    equipment_cost: float = Field(description="Equipment cost")
    civil_works: float = Field(description="Civil works")
    installation_piping: float = Field(description="Installation and piping")
    engineering_supervision: float = Field(description="Engineering and supervision")
    contingency: float | None = Field(default=None, description="Contingencies")


class OperationalCosts(BaseSchema):
    """Annual operational costs"""

    electrical_energy: float = Field(description="Annual electrical energy")
    chemicals: float = Field(description="Annual chemicals")
    personnel: float = Field(description="Annual operating personnel")
    maintenance_spare_parts: float = Field(description="Annual maintenance and spare parts")


class OperationalData(BaseSchema):
    """System operational data"""

    required_area_m2: float = Field(description="Required area in m²")
    sludge_production_kg_day: float | None = Field(
        default=None, description="Sludge production kg/day"
    )
    energy_consumption_kwh_m3: float | None = Field(
        default=None, description="Energy consumption kWh/m³"
    )


class DesignParameters(BaseSchema):
    """Design parameters calculated by agent"""

    peak_factor: float = Field(description="Peak flow factor (calculated based on project)")
    safety_factor: float = Field(description="Safety factor for regulatory compliance")
    operating_hours: int = Field(description="Daily operating hours based on client operations")
    design_life_years: int = Field(description="Equipment design life in years")
    regulatory_margin_percent: float = Field(
        default=20.0, description="Regulatory compliance margin %"
    )


class WaterParameter(BaseSchema):
    """Flexible water quality parameter for any sector"""

    parameter: str = Field(description="Parameter name (e.g., BOD, Heavy metals, pH, Chromium)")
    value: float = Field(description="Parameter value")
    unit: str = Field(description="Unit (mg/L, unitless, °C, etc.)")
    target_value: float | None = Field(default=None, description="Target effluent value")


class InfluentCharacteristics(BaseSchema):
    """Flexible influent characteristics - water quality only (flow is in TechnicalData)"""

    parameters: list[WaterParameter] = Field(
        description="Water quality parameters specific to this sector and project"
    )


class ProjectRequirements(BaseSchema):
    """Project requirements and constraints"""

    influent_characteristics: InfluentCharacteristics = Field(
        description="Input water quality parameters"
    )
    discharge_requirements: list[str] = Field(
        min_length=1, description="Required effluent quality targets"
    )
    business_objectives: list[str] = Field(
        min_length=1, description="Client business goals"
    )
    site_constraints: list[str] = Field(
        description="Physical/operational constraints"
    )


class SelectedTechnology(BaseSchema):
    """Technology selected for treatment stage"""

    stage: str = Field(description="Treatment stage: primary/secondary/tertiary")
    technology: str = Field(description="Technology name")
    justification: str = Field(description="Technical reasoning for selection")


class RejectedAlternative(BaseSchema):
    """Alternative technology considered but not selected"""

    technology: str = Field(description="Technology name")
    reason_rejected: str = Field(description="Why it was rejected")
    stage: str | None = Field(default=None, description="Stage it was considered for")


class TechnologySelection(BaseSchema):
    """Technology selection with justifications"""

    selected_technologies: list[SelectedTechnology] = Field(
        min_length=1, description="Technologies selected (at least one required)"
    )
    rejected_alternatives: list[RejectedAlternative] = Field(
        description="Technologies considered but rejected"
    )


class TechnicalData(BaseSchema):
    """Complete technical system data - single source of truth"""

    design_flow_m3_day: float = Field(gt=0, description="Design flow rate in m³/day")
    main_equipment: list[EquipmentSpec] = Field(
        min_length=1, description="Main equipment list (at least one required)"
    )
    implementation_months: int = Field(gt=0, description="Implementation duration")
    design_parameters: DesignParameters
    project_requirements: ProjectRequirements
    assumptions: list[str] = Field(min_length=1, description="Design assumptions")
    technology_selection: TechnologySelection
    treatment_efficiency: TreatmentEfficiency
    capex_breakdown: FinancialBreakdown
    opex_breakdown: OperationalCosts
    operational_data: OperationalData
    payback_years: float | None = None
    annual_savings_usd: float | None = None
    roi_percent: float | None = None

    @computed_field
    @property
    def capex_usd(self) -> float:
        """Total CAPEX computed from breakdown"""
        return sum([
            self.capex_breakdown.equipment_cost,
            self.capex_breakdown.civil_works,
            self.capex_breakdown.installation_piping,
            self.capex_breakdown.engineering_supervision,
            self.capex_breakdown.contingency or 0,
        ])

    @computed_field
    @property
    def annual_opex_usd(self) -> float:
        """Total annual OPEX computed from breakdown"""
        return sum([
            self.opex_breakdown.electrical_energy,
            self.opex_breakdown.chemicals,
            self.opex_breakdown.personnel,
            self.opex_breakdown.maintenance_spare_parts,
        ])

    @model_validator(mode="after")
    def validate_costs(self) -> "TechnicalData":
        """Validate cost breakdowns are positive"""
        # CAPEX validation
        if self.capex_breakdown.equipment_cost < 0:
            raise ValueError("Equipment cost cannot be negative")
        if self.capex_breakdown.civil_works < 0:
            raise ValueError("Civil works cost cannot be negative")
        if self.capex_breakdown.installation_piping < 0:
            raise ValueError("Installation cost cannot be negative")
        if self.capex_breakdown.engineering_supervision < 0:
            raise ValueError("Engineering cost cannot be negative")

        # OPEX validation
        if self.opex_breakdown.electrical_energy < 0:
            raise ValueError("Electrical energy cost cannot be negative")
        if self.opex_breakdown.chemicals < 0:
            raise ValueError("Chemicals cost cannot be negative")
        if self.opex_breakdown.personnel < 0:
            raise ValueError("Personnel cost cannot be negative")
        if self.opex_breakdown.maintenance_spare_parts < 0:
            raise ValueError("Maintenance cost cannot be negative")

        return self


class ProposalOutput(BaseSchema):
    """
    Complete technical proposal output from AI agent.

    This is what the Pydantic-AI agent returns after processing
    user input (FlexibleWaterProjectData).
    """

    markdown_content: str = Field(description="Proposal content in markdown format")
    technical_data: TechnicalData = Field(description="Structured technical data")

    confidence_level: Literal["High", "Medium", "Low"] = Field(
        description="Agent's confidence in proposal (REQUIRED)"
    )
    recommendations: list[str] | None = Field(
        default=None, description="Additional recommendations"
    )
