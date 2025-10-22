"""
Proposal Output Models - Data that flows FROM AI agent TO user.

This module contains structured Pydantic models for AI-generated proposals:
- Equipment specifications with technical details
- Treatment efficiency metrics
- Cost breakdowns (CAPEX/OPEX)
- Design parameters and justifications

These models define what the AI agent MUST return after analyzing user input.
"""

from typing import Optional, List, Dict, Any
from pydantic import Field
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
    justification: Optional[str] = Field(
        default=None, description="Technical justification for equipment selection"
    )

    # Semantic fields for intelligent visualization
    criticality: Optional[str] = Field(
        default="medium", description="Equipment criticality: high/medium/low"
    )
    stage: Optional[str] = Field(
        default="secondary",
        description="Treatment stage: primary/secondary/tertiary/auxiliary",
    )
    risk_factor: Optional[float] = Field(
        default=0.5, description="Operational risk factor: 0.0-1.0"
    )


class TreatmentParameter(BaseSchema):
    """
    Treatment performance for a single water quality parameter.

    Supports ANY parameter from user input: BOD, COD, Chromium VI, Mercury,
    Pharmaceuticals, PFAS, custom contaminants, etc.

    This model is fully flexible and accepts any parameter name the user provides.
    """

    parameter_name: str = Field(
        description="Parameter name EXACTLY as provided by user (preserve casing)"
    )
    influent_concentration: Optional[float] = Field(
        default=None, description="Input concentration value from user data"
    )
    effluent_concentration: Optional[float] = Field(
        default=None, description="Expected output concentration after treatment"
    )
    removal_efficiency_percent: float = Field(
        ge=0, le=100, description="Removal efficiency percentage (0-100)"
    )
    unit: str = Field(
        default="mg/L", description="Measurement unit (inherited from input or standard)"
    )

    # Engineering context
    treatment_stage: Optional[str] = Field(
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

    parameters: List[TreatmentParameter] = Field(
        description="Treatment performance for each water quality parameter from user input"
    )

    overall_compliance: bool = Field(
        default=True, description="All parameters meet regulatory requirements"
    )
    critical_parameters: Optional[List[str]] = Field(
        default=None, description="Parameters requiring special attention or close monitoring"
    )


class FinancialBreakdown(BaseSchema):
    """Basic financial breakdown"""

    equipment_cost: float = Field(description="Equipment cost")
    civil_works: float = Field(description="Civil works")
    installation_piping: float = Field(description="Installation and piping")
    engineering_supervision: float = Field(description="Engineering and supervision")
    contingency: Optional[float] = Field(default=None, description="Contingencies")


class OperationalCosts(BaseSchema):
    """Annual operational costs"""

    electrical_energy: float = Field(description="Annual electrical energy")
    chemicals: float = Field(description="Annual chemicals")
    personnel: float = Field(description="Annual operating personnel")
    maintenance_spare_parts: float = Field(description="Annual maintenance and spare parts")


class ClientInformation(BaseSchema):
    """Client information"""

    company_name: str = Field(description="Company name")
    industry: str = Field(description="Industrial sector")
    subsector: str = Field(description="Project subsector")
    location: str = Field(description="Project location")


class OperationalData(BaseSchema):
    """System operational data"""

    required_area_m2: float = Field(description="Required area in m²")
    sludge_production_kg_day: Optional[float] = Field(
        default=None, description="Sludge production kg/day"
    )
    energy_consumption_kwh_m3: Optional[float] = Field(
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
    target_value: Optional[float] = Field(default=None, description="Target effluent value")


class InfluentCharacteristics(BaseSchema):
    """Flexible influent characteristics for any industrial sector"""

    flow_rate_m3_day: float = Field(description="Flow rate in m³/day")
    parameters: List[WaterParameter] = Field(
        description="Water quality parameters specific to this sector and project"
    )


class ProblemAnalysis(BaseSchema):
    """Detailed problem analysis data"""

    influent_characteristics: InfluentCharacteristics = Field(
        description="Input water quality data"
    )
    quality_objectives: List[str] = Field(description="Project-specific quality objectives")
    conditions_restrictions: List[str] = Field(
        description="Site-specific conditions and restrictions"
    )


class AlternativeAnalysis(BaseSchema):
    """Alternative technology analysis"""

    technology: str = Field(description="Alternative technology considered")
    reason_rejected: str = Field(description="Technical/economic reason for rejection")


class TechnologyJustification(BaseSchema):
    """Detailed technology selection justification"""

    technology: str = Field(description="Selected technology name")
    alternatives_considered: List[str] = Field(description="Alternative technologies evaluated")
    selection_criteria: str = Field(description="Primary selection criterion")
    technical_justification: str = Field(description="Detailed technical reasoning")


class TechnicalData(BaseSchema):
    """Complete technical system data"""

    flow_rate_m3_day: float = Field(description="Design flow rate in m³/day")
    main_equipment: List[EquipmentSpec] = Field(description="Main equipment list")
    capex_usd: float = Field(description="Total capital investment in USD")
    annual_opex_usd: float = Field(description="Annual operational costs in USD")
    implementation_months: int = Field(description="Implementation duration in months")

    # Design parameters calculated by agent
    design_parameters: DesignParameters = Field(description="Technical design parameters")
    project_objectives: List[str] = Field(description="Specific project objectives from client")

    # Detailed analysis sections for PDF generation
    problem_analysis: ProblemAnalysis = Field(description="Detailed problem analysis data")
    alternative_analysis: List[AlternativeAnalysis] = Field(
        description="Technologies considered but rejected"
    )
    assumptions: List[str] = Field(description="Project-specific design assumptions")
    technology_justification: List[TechnologyJustification] = Field(
        description="Detailed technology justifications"
    )

    # Structured information for charts
    treatment_efficiency: TreatmentEfficiency = Field(
        description="Treatment efficiency for all user-provided parameters"
    )
    capex_breakdown: FinancialBreakdown = Field(
        description="CAPEX breakdown - REQUIRED, calculated from engineering analysis"
    )
    opex_breakdown: OperationalCosts = Field(
        description="OPEX breakdown - REQUIRED, calculated from engineering analysis"
    )
    client_info: ClientInformation = Field(description="Client information")
    operational_data: OperationalData = Field(description="Operational data")

    # Financial metrics
    payback_years: Optional[float] = Field(default=None, description="Payback period in years")
    annual_savings_usd: Optional[float] = Field(default=None, description="Annual savings in USD")
    roi_percent: Optional[float] = Field(default=None, description="ROI in %")


class ProposalOutput(BaseSchema):
    """
    Complete technical proposal output from AI agent.

    This is what the Pydantic-AI agent returns after processing
    user input (FlexibleWaterProjectData).
    """

    markdown_content: str = Field(description="Proposal content in markdown format")
    technical_data: TechnicalData = Field(description="Structured technical data")

    # Optional fields
    confidence_level: Optional[str] = Field(default="High", description="Confidence level")
    recommendations: Optional[List[str]] = Field(
        default=None, description="Additional recommendations"
    )

    # Compatibility with existing charts system
    @property
    def data_for_charts(self) -> Dict[str, Any]:
        """Compatibility with existing charts system"""
        return self.technical_data.model_dump()
