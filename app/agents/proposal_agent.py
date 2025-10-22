"""
AI Agent for generating technical proposals.
Ported from backend-chatbot with adaptations for FlexibleWaterProjectData.
Includes proven cases tool and full engineering capabilities with deviation tracking.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.usage import UsageLimits
from pydantic_ai.settings import ModelSettings
import json
from pathlib import Path

from app.models.project_input import FlexibleWaterProjectData
from app.models.proposal_output import ProposalOutput
from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe storage for proven cases consulted during generation
_proven_cases_context = {}


def _log_deviation_analysis(
    proposal_output: ProposalOutput, client_metadata: Dict[str, Any]
) -> None:
    """
    Analyze and log deviations between agent selection and proven cases.

    This provides visibility into whether the agent is following proven precedents
    or making autonomous engineering decisions.
    """
    # Get context key
    context_key = f"{client_metadata.get('company_name', 'unknown')}_{client_metadata.get('selected_sector', 'unknown')}"
    proven_cases = _proven_cases_context.get(context_key)

    if not proven_cases or not proven_cases.get("similar_cases"):
        logger.info("💡 No proven cases were consulted - agent designed from first principles")
        return

    # Extract agent's selected treatment train
    selected_equipment = proposal_output.technical_data.main_equipment
    if not selected_equipment:
        return

    # Build selected train (only PRIMARY, SECONDARY, TERTIARY)
    selected_technologies = [
        eq.type for eq in selected_equipment if eq.stage in ["primary", "secondary", "tertiary"]
    ]
    selected_train_str = " + ".join(selected_technologies)

    # Get first proven case (most relevant)
    proven_case = proven_cases["similar_cases"][0]
    proven_train = proven_case.get("treatment_train", "")

    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║          PROVEN CASE vs AGENT SELECTION COMPARISON          ║")
    logger.info("╠══════════════════════════════════════════════════════════════╣")
    logger.info(f"║ 📚 Proven Case: {proven_case.get('application_type', 'Unknown')}")
    logger.info(f"║    Train: {proven_train}")
    logger.info(f"║")
    logger.info(f"║ 🔧 Agent Selected:")
    logger.info(f"║    Train: {selected_train_str}")
    logger.info("╠══════════════════════════════════════════════════════════════╣")

    # Analyze deviations
    proven_train_lower = proven_train.lower()
    selected_train_lower = selected_train_str.lower()

    # Key technologies to check
    tech_checks = {
        "SBR": "sbr",
        "MBBR": "mbbr",
        "UASB": "uasb",
        "MBR": "mbr",
        "DAF": "daf",
        "Chlorination": "chlorination",
        "UV": "uv",
        "RO": "ro",
        "GAC": "gac",
    }

    deviations_found = []
    additions_found = []

    for tech_name, tech_key in tech_checks.items():
        in_proven = tech_key in proven_train_lower
        in_selected = tech_key in selected_train_lower

        if in_proven and not in_selected:
            deviations_found.append(f"   ⚠️  {tech_name} was in proven case but NOT selected")
        elif not in_proven and in_selected:
            additions_found.append(f"   ➕ {tech_name} was NOT in proven case but WAS selected")

    if deviations_found or additions_found:
        logger.warning("║ ⚠️  DEVIATIONS DETECTED:")
        for deviation in deviations_found:
            logger.warning(f"║ {deviation}")
        for addition in additions_found:
            logger.warning(f"║ {addition}")
        logger.warning("║")
        logger.warning("║ 💡 Review 'Alternative Analysis' and 'Technology Justification'")
        logger.warning("║    sections in the proposal for engineering rationale")
    else:
        logger.info("║ ✅ Agent selection aligns with proven case recommendations")

    logger.info("╚══════════════════════════════════════════════════════════════╝")

    # ⚠️ DO NOT clean up context here - it's needed by proposal_service.py
    # The context will be cleaned up after saving to database


class ProposalGenerationError(Exception):
    """Custom exception for proposal generation failures"""

    pass


# Simple data structure for the agent
@dataclass
class ProposalContext:
    """Simple context for proposal generation"""

    water_data: FlexibleWaterProjectData
    client_metadata: Dict[str, Any]


# Configure OpenAI API
if not os.getenv("OPENAI_API_KEY") and settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

if not os.getenv("OPENAI_API_KEY"):
    logger.error("OpenAI API key not found")
    raise ValueError("OpenAI API key required")


def load_proposal_prompt() -> str:
    """
    Load water treatment proposal prompt from external markdown file.
    Follows 2025 best practices for prompt management in production AI applications.
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "prompt-for-proposal.md"

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise ValueError(f"Prompt file is empty: {prompt_path}")

        logger.info(f"✅ Loaded prompt template from: {prompt_path.name}")
        return content

    except FileNotFoundError:
        logger.error(f"❌ Prompt file not found: {prompt_path}")
        raise
    except Exception as e:
        logger.error(f"❌ Error loading prompt: {e}")
        raise


proposal_agent = Agent(
    f"openai:{settings.OPENAI_MODEL}",  # Read from .env for flexibility
    deps_type=ProposalContext,
    output_type=ProposalOutput,
    instructions=load_proposal_prompt(),
    model_settings=ModelSettings(
        temperature=0.2,
    ),
    retries=3,
)


# Dynamic data injection using @instructions
@proposal_agent.instructions
def inject_company_context(ctx: RunContext[ProposalContext]) -> str:
    """Inject dynamic company and project context"""
    client_metadata = ctx.deps.client_metadata

    return f"""
PROJECT CONTEXT:
Company: {client_metadata.get("company_name", "Client Company")}
Industry: {client_metadata.get("selected_sector", "Industrial")}
Subsector: {client_metadata.get("selected_subsector", "General")}
Location: {client_metadata.get("user_location", "Not specified")}
"""


@proposal_agent.instructions
def inject_water_project_data(ctx: RunContext[ProposalContext]) -> str:
    """
    Inject clean water treatment project data for AI analysis.

    Uses to_ai_context() to extract ONLY relevant values without UI metadata,
    reducing token count by ~85% and improving AI focus.
    """
    water_data = ctx.deps.water_data

    # Extract clean context (no id, type, source, importance metadata)
    ai_context = water_data.to_ai_context()

    # Format as readable markdown
    formatted_context = water_data.format_ai_context_to_string(ai_context)

    return f"""
WATER PROJECT ANALYSIS DATA:
{formatted_context}
"""


@proposal_agent.instructions
def inject_client_requirements(ctx: RunContext[ProposalContext]) -> str:
    """Inject additional client metadata and requirements"""
    client_metadata = ctx.deps.client_metadata
    metadata_json = json.dumps(client_metadata, indent=2)

    return f"""
CLIENT REQUIREMENTS & METADATA:
{metadata_json}
"""


@proposal_agent.tool(retries=2, docstring_format="google")
async def get_proven_water_treatment_cases(
    ctx: RunContext[ProposalContext],
) -> Dict[str, Any]:
    """Get 2-3 proven water treatment cases from similar sectors.

    Returns treatment trains, cost benchmarks, and specs for engineering validation.

    Returns:
        Dict with similar_cases (list), user_sector (str), message (str).
    """
    try:
        logger.info(
            f"🔍 Accessing proven cases database for {ctx.deps.client_metadata.get('selected_sector', 'project')}"
        )

        # Import here to avoid circular dependency
        from app.agents.tools.intelligent_case_filter import (
            get_engineering_references,
        )

        # Get intelligently filtered cases based on project context
        cases = await get_engineering_references(ctx)

        # Log the intelligent filtering results
        similar_cases_count = len(cases.get("similar_cases", []))
        sector = cases.get("user_sector", "unknown")

        logger.info(f"✅ Found {similar_cases_count} similar cases for sector: {sector}")

        # Store cases in context using client metadata as key for later comparison
        context_key = f"{ctx.deps.client_metadata.get('company_name', 'unknown')}_{ctx.deps.client_metadata.get('selected_sector', 'unknown')}"
        _proven_cases_context[context_key] = cases

        return cases

    except Exception as e:
        logger.error(f"❌ Error accessing proven cases database: {e}")
        raise ModelRetry(
            f"Unable to access proven cases database: {e}. The agent will design based on general engineering principles."
        )


# ═══════════════════════════════════════════════════════════════════
# 🔧 DETERMINISTIC ENGINEERING CALCULATION TOOLS
# ═══════════════════════════════════════════════════════════════════
# These tools provide REPRODUCIBLE engineering calculations.
# Key characteristics:
# - DETERMINISTIC: Same inputs → Same outputs
# - VERIFIABLE: Show formulas and sources
# - NO LLM: Pure mathematical calculations
# - AUDITABLE: Full calculation trace
# ═══════════════════════════════════════════════════════════════════


@proposal_agent.tool_plain(retries=1, docstring_format="google")
def calculate_mass_balance(flow_m3_day: float, concentrations: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate contaminant mass loads (kg/day) from concentrations.

    Formula: Load = Flow × Concentration × 0.001
    Accepts flexible formats (numbers, strings with units, dicts).
    Supports: mg/L, g/L, ppm, µg/L, kg/m³ (auto-converts to mg/L).

    Args:
        flow_m3_day: Flow rate (m³/day)
        concentrations: Dict of parameters {"BOD": 3700} or {"BOD": "3700 mg/L"}

    Returns:
        Dict with loads (kg/day), formulas, and conversion traces per parameter.
    """
    from app.agents.tools.engineering_calculations import calculate_mass_balance as calc_func

    logger.info(f"🧮 DETERMINISTIC TOOL: Calculating mass balance for flow={flow_m3_day} m³/d")
    result = calc_func(flow_m3_day, concentrations)
    logger.info(f"✅ Mass balance calculated: {len(result['loads'])} parameters")

    return result


@proposal_agent.tool_plain(retries=1, docstring_format="google")
def size_biological_reactor(
    reactor_type: str,
    organic_load_kg_day: float,
    flow_m3_day: float,
    temperature_celsius: float = 25.0,
) -> Dict[str, Any]:
    """Size biological reactor (UASB, SBR, MBR, Activated Sludge).

    Uses industry design criteria (Metcalf & Eddy, WEF, EPA).
    Returns volume (m³), HRT (hours), dimensions, and design criteria.

    Args:
        reactor_type: "UASB", "SBR", "MBR", or "activated_sludge"
        organic_load_kg_day: COD for anaerobic, BOD for aerobic (kg/day)
        flow_m3_day: Flow rate (m³/day)
        temperature_celsius: Operating temp (°C, default 25)

    Returns:
        Dict with volume, HRT, dimensions, design_criteria, validation, warnings.
    """
    from app.agents.tools.engineering_calculations import size_biological_reactor as size_func

    logger.info(
        f"🧮 DETERMINISTIC TOOL: Sizing {reactor_type} reactor (load={organic_load_kg_day} kg/d, flow={flow_m3_day} m³/d)"
    )
    result = size_func(reactor_type, organic_load_kg_day, flow_m3_day, temperature_celsius)
    logger.info(f"✅ {reactor_type} sized: {result['volume_m3']} m³, HRT={result['hrt_hours']}h")

    return result


@proposal_agent.tool_plain(retries=1, docstring_format="google")
def validate_treatment_efficiency(
    technology_train: list,
    influent: Dict[str, Any],
    required_removal_pct: Optional[Dict[str, float]] = None,
    effluent_limits_mg_l: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Validate treatment train engineering LOGIC (not exact removal simulation).

    Checks if train follows sound engineering principles. Works for ANY technology.
    Returns logic assessment, checks passed, and ADVISORY warnings (not blocking).

    Key logic checks:
    - High FOG/oil → Flotation upstream of biological
    - High organics → Biological treatment present
    - Train complexity → Reasonable stages (4-8 typical)
    - Sequence → Logical progression

    IMPORTANT: Warnings are ADVISORY only. If you followed a proven case,
    trust the proven case evidence over this logic check.

    Args:
        technology_train: List of technologies ["Screening", "DAF", "SBR", "GAC", "UV"]
        influent: Dict of concentrations {"BOD": 3700, "FOG": 900}
        required_removal_pct: OPTIONAL - Not used in logic validation
        effluent_limits_mg_l: OPTIONAL - Not used in logic validation

    Returns:
        Dict with overall_achievable (bool), logic_checks (list), warnings (list).
    """
    from app.agents.tools.engineering_calculations import (
        validate_treatment_efficiency as validate_func,
    )

    # Parse influent: convert strings to floats if needed
    clean_influent = {}
    for key, value in influent.items():
        if isinstance(value, str):
            try:
                clean_influent[key] = float(value.split()[0])
            except (ValueError, IndexError):
                clean_influent[key] = float(value)
        else:
            clean_influent[key] = float(value)

    logger.info(f"🧮 LOGIC CHECK: Validating train {' → '.join(technology_train)}")
    result = validate_func(
        technology_train, clean_influent, required_removal_pct, effluent_limits_mg_l
    )

    status = "Sound" if result["overall_achievable"] else "Advisory warnings"
    logger.info(f"✅ Logic validation: {status}")

    if result["logic_checks"]:
        logger.info(f"   Passed checks: {len(result['logic_checks'])}")

    if result["warnings"]:
        logger.warning(f"⚠️  Advisory warnings: {len(result['warnings'])} (not blocking)")

    return result


@proposal_agent.tool_plain(retries=1, docstring_format="google")
def calculate_total_capex(
    equipment_costs: Dict[str, float], location_factor: float = 1.0
) -> Dict[str, Any]:
    """Calculate total CAPEX from equipment costs with industry-standard build-up.

    Applies percentages for civil works, installation, E&I, engineering, contingency.
    Auto-detects complexity (1-3=simple, 4-5=medium, 6+=complex) for percentage scaling.

    Args:
        equipment_costs: Dict of equipment costs {"Equipment Name": cost_usd}
        location_factor: Regional multiplier (default 1.0, LATAM 0.8)

    Returns:
        Dict with total_capex, breakdown by category, calculation trace, complexity.
    """
    from app.agents.tools.engineering_calculations import calculate_total_capex as calc_func

    # Auto-detect complexity based on equipment count
    num_equipment = len(equipment_costs)

    if num_equipment <= 3:
        complexity = "simple"
    elif num_equipment <= 5:
        complexity = "medium"
    else:
        complexity = "complex"

    logger.info(
        f"🧮 DETERMINISTIC TOOL: Calculating CAPEX ({num_equipment} equipment → {complexity} complexity)"
    )
    result = calc_func(equipment_costs, complexity, location_factor)

    # Add complexity detection to result for transparency
    result["complexity_detected"] = complexity
    result["equipment_count"] = num_equipment

    logger.info(f"✅ CAPEX calculated: ${result['total_capex']:,.0f} ({complexity} complexity)")

    return result


@proposal_agent.tool_plain(retries=1, docstring_format="google")
def calculate_annual_opex(
    equipment_power_kw: Dict[str, float],
    flow_m3_day: float,
    operating_hours_per_day: float = 24.0,
    electricity_rate_usd_kwh: float = 0.12,
    chemicals_usd_per_m3: float = 0.50,
    operators_count: int = 2,
    operator_annual_salary_usd: float = 25000.0,
    maintenance_pct_capex: float = 0.04,
    capex_usd: float = 0.0,
) -> Dict[str, Any]:
    """Calculate annual OPEX across 4 categories: electricity, chemicals, personnel, maintenance.

    Returns total annual cost, breakdown by category, unit cost ($/m³), and calculation trace.

    Args:
        equipment_power_kw: REQUIRED DICT FORMAT - A dictionary mapping each equipment name to its power (kW).

                           ❌ WRONG: 80 (single number)
                           ❌ WRONG: [15, 30, 20] (list)
                           ✅ CORRECT: {"DAF": 15, "SBR Blower": 30, "MBR": 20, "Pumps": 15}

                           You MUST create a dict with equipment names as keys and power (kW) as values.
                           If you have 4 equipment items, create dict with 4 key-value pairs.

        flow_m3_day: Design flow rate (m³/day)
        operating_hours_per_day: Hours/day (default 24)
        electricity_rate_usd_kwh: $/kWh (default 0.12)
        chemicals_usd_per_m3: $/m³ (default 0.50)
        operators_count: Number of operators (default 2)
        operator_annual_salary_usd: $/year per operator (default 25000)
        maintenance_pct_capex: % of CAPEX (default 4%)
        capex_usd: Total CAPEX for maintenance calc

    Returns:
        Dict with total_opex_annual, opex_per_m3, breakdown by category, trace.
    """
    from app.agents.tools.engineering_calculations import calculate_annual_opex as calc_func

    logger.info(f"🧮 DETERMINISTIC TOOL: Calculating annual OPEX for {flow_m3_day} m³/d")
    result = calc_func(
        equipment_power_kw,
        flow_m3_day,
        operating_hours_per_day,
        electricity_rate_usd_kwh,
        chemicals_usd_per_m3,
        operators_count,
        operator_annual_salary_usd,
        maintenance_pct_capex,
        capex_usd,
    )
    logger.info(
        f"✅ OPEX calculated: ${result['total_opex_annual']:,.0f}/year (${result['opex_per_m3']:.2f}/m³)"
    )

    return result


# COMMENTED OUT - Tool was being called before technical_data was ready
# Causing ValidationError: Field required [type=missing]
# TODO: Re-enable after fixing execution order or making technical_data optional
#
# @proposal_agent.tool_plain(retries=1, docstring_format="google")
# def validate_proposal_consistency(
#     markdown_content: str, technical_data: Dict[str, Any]
# ) -> Dict[str, Any]:
#     """Validate markdown numbers match JSON technical data (CAPEX, OPEX, flow).
#
#     Checks key values match between markdown and JSON (1% tolerance).
#     Call before returning ProposalOutput. If inconsistent, fix and re-validate.
#
#     Args:
#         markdown_content: Full markdown proposal text
#         technical_data: TechnicalData as dict (use .model_dump())
#
#     Returns:
#         Dict with consistent (bool), mismatches list, detailed_checks, recommendations.
#     """
#     from app.agents.tools.engineering_calculations import (
#         validate_proposal_consistency as validate_func,
#     )
#
#     logger.info("🧮 DETERMINISTIC TOOL: Validating markdown-JSON consistency")
#     result = validate_func(markdown_content, technical_data)
#
#     if result["consistent"]:
#         logger.info(f"✅ Consistency check PASSED - {result['checks_performed']} checks OK")
#     else:
#         logger.error(f"❌ Consistency check FAILED - {len(result['mismatches'])} mismatches found:")
#         for mismatch in result["mismatches"]:
#             logger.error(f"   ⚠️  {mismatch}")
#
#     if result["warnings"]:
#         for warning in result["warnings"]:
#             logger.warning(f"   ⚠️  {warning}")
#
#     return result


async def generate_enhanced_proposal(
    water_data: FlexibleWaterProjectData,
    client_metadata: Optional[Dict[str, Any]] = None,
) -> ProposalOutput:
    """
    Generate water treatment proposal using AI agent.

    Args:
        water_data: FlexibleWaterProjectData with user-defined fields
        client_metadata: Client metadata dict from user profile and project

    Returns:
        ProposalOutput: Complete technical proposal with structured data
    """
    if client_metadata is None:
        client_metadata = {}

    try:
        logger.info("🧠 Starting proposal generation...")

        # ═══════════════════════════════════════════════════════════════════
        # 🔍 LOG CLEAN DATA SENT TO AI AGENT
        # ═══════════════════════════════════════════════════════════════════
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║         📨 CLEAN DATA SENT TO AI AGENT (No Metadata)         ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")

        # 1. Extract and log clean AI context
        ai_context = water_data.to_ai_context()
        ai_context_json = json.dumps(ai_context, indent=2, ensure_ascii=False)

        logger.info("🎯 CLEAN AI CONTEXT:")
        logger.info(f"\n{ai_context_json}")

        # 2. Show formatted string preview (what actually gets injected)
        formatted_context = water_data.format_ai_context_to_string(ai_context)
        logger.info("\n📝 FORMATTED CONTEXT (for prompt injection):")
        logger.info(
            f"\n{formatted_context[:500]}..."
            if len(formatted_context) > 500
            else f"\n{formatted_context}"
        )

        # 3. Log client metadata
        metadata_json = json.dumps(client_metadata, indent=2, ensure_ascii=False)
        logger.info("\n🏢 CLIENT METADATA:")
        logger.info(f"\n{metadata_json}")

        # 4. Token efficiency info
        full_json = water_data.model_dump_json(exclude_none=True)
        logger.info("\n💡 EFFICIENCY:")
        logger.info(f"  Full serialization: {len(full_json)} chars")
        logger.info(f"  Clean context: {len(formatted_context)} chars")
        logger.info(
            f"  Reduction: {round((1 - len(formatted_context) / len(full_json)) * 100, 1)}%"
        )

        logger.info("════════════════════════════════════════════════════════════════")

        # Create context - data will be injected via @instructions
        context = ProposalContext(
            water_data=water_data,
            client_metadata=client_metadata,
        )

        # Run agent with usage limits
        result = await proposal_agent.run(
            "Generate a comprehensive water treatment proposal with technical specifications, cost analysis, and implementation timeline.",
            deps=context,
            usage_limits=UsageLimits(
                request_limit=18,
                total_tokens_limit=200000,
            ),
        )

        # Log success with token usage
        usage = result.usage()
        if usage:
            logger.info(f"✅ Proposal generated successfully")
            logger.info(
                f"📊 Token usage: {usage.total_tokens:,} / 180,000 ({usage.total_tokens / 1800:.1f}%)"
            )
            # Note: RunUsage doesn't have request_count attribute in pydantic-ai
            # Use usage.requests if available or skip logging request count
            try:
                if hasattr(usage, "requests"):
                    logger.info(f"📊 API requests: {len(usage.requests)}")
            except:
                pass

            # Warn if approaching limit
            if usage.total_tokens > 150000:
                logger.warning(
                    f"⚠️  HIGH TOKEN USAGE: {usage.total_tokens:,} tokens (>150K). "
                    f"Consider optimizing prompt or increasing limit."
                )

        # 🔍 INSPECT OUTPUT FOR TOKEN ANALYSIS
        try:
            markdown_chars = len(result.output.markdown_content)
            markdown_words = len(result.output.markdown_content.split())
            markdown_lines = len(result.output.markdown_content.split("\n"))

            logger.info("╔══════════════════════════════════════════════════════════════╗")
            logger.info("║          📝 MARKDOWN CONTENT ANALYSIS                        ║")
            logger.info("╠══════════════════════════════════════════════════════════════╣")
            logger.info(f"║ Characters: {markdown_chars:,}")
            logger.info(f"║ Words: {markdown_words:,}")
            logger.info(f"║ Lines: {markdown_lines}")
            logger.info(f"║ Est. tokens: {int(markdown_words * 1.3):,} (words × 1.3)")
            logger.info("╠══════════════════════════════════════════════════════════════╣")
            logger.info("║ First 500 characters:")
            logger.info(f"║ {result.output.markdown_content[:500]}")
            logger.info("╚══════════════════════════════════════════════════════════════╝")
        except Exception as inspect_error:
            logger.debug(f"Could not inspect markdown output: {inspect_error}")
        else:
            logger.info("✅ Proposal generated successfully")

        # Log deviation analysis (agent vs proven cases)
        try:
            _log_deviation_analysis(result.output, client_metadata)
        except Exception as log_error:
            logger.debug(f"Could not perform deviation analysis: {log_error}")

        return result.output

    except Exception as e:
        logger.error(f"❌ Error generating proposal: {e}", exc_info=True)
        raise ProposalGenerationError(f"Failed to generate proposal: {e}")
