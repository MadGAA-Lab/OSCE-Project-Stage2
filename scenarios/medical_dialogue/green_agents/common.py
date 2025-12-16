from typing import Literal

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from pydantic import BaseModel


# ==================== Data Models ====================

class CriterionEvaluation(BaseModel):
    """Evaluation of a single criterion"""
    criterion_id: int  # Criterion number from CSV (1-30)
    criterion_text: str  # The criterion being evaluated
    category: str  # "Empathy", "Persuasion", or "Safety"
    status: Literal["met", "not_met", "not_relevant"]  # Evaluation status
    evidence: str | None = None  # Brief explanation/evidence for the judgment

class PatientPersona(BaseModel):
    """Minimal patient persona config - details generated dynamically"""
    persona_id: str  # e.g., "INTJ_PNEUMO" or "INTJ_M_PNEUMO"
    mbti_type: str  # MBTI personality type (16 options: INTJ, ESFP, etc.)
    gender: str | None = None  # "male" or "female" (optional - can be generated)
    medical_case: str  # "pneumothorax" or "lung_cancer"
    character_description: str  # Generated complete character description for patient agent


class PatientRoleplayExamples(BaseModel):
    """Generated roleplay examples for context priming"""
    role_core_description: str  # Detailed character description (goes in USER message, not system)
    role_acknowledgement_phrase: str  # Acknowledgement after receiving core description
    role_rules_and_constraints: str  # Rules and constraints for staying in character
    role_confirmation_phrase: str  # Confirmation after receiving rules
    example_say: str  # Example dialogue from this patient
    example_think: str  # Example inner thoughts of this patient
    example_do: str  # Example action/behavior of this patient


class PatientBackground(BaseModel):
    """Full patient background info generated for simulation (superset of clinical info)"""
    # Basic demographics
    age: int  # Patient age (35-65 range)
    gender: str  # "male" or "female" (generated if not specified)
    occupation: str  # Job/profession aligned with personality
    
    # Medical information
    medical_case: str  # "pneumothorax" or "lung_cancer"
    symptoms: str  # Current symptoms the patient is experiencing
    diagnosis: str  # Medical diagnosis
    recommended_treatment: str  # Recommended surgical procedure
    treatment_risks: str  # Risks associated with the treatment
    treatment_benefits: str  # Benefits of the treatment
    prognosis_with_treatment: str  # Expected outcome with treatment
    prognosis_without_treatment: str  # Expected outcome without treatment
    
    # Personal background (for patient simulation only)
    family_situation: str  # Family context
    lifestyle: str  # Lifestyle and habits
    values: str  # Personal values
    concerns_and_fears: str  # Personality-driven concerns about medical situation


class PatientClinicalInfo(BaseModel):
    """Partial patient information provided to Doctor Agent (NO personality traits)
    
    This is a subset of PatientBackground - only includes information that
    a real doctor would have access to in a clinical setting.
    Does NOT include: symptoms (patient reports these), personality, concerns, lifestyle.
    """
    age: int  # Patient age
    gender: str | None = None  # "male" or "female" (optional for privacy)
    medical_case: str  # "pneumothorax" or "lung_cancer"
    diagnosis: str  # Medical diagnosis from tests/imaging
    recommended_treatment: str  # Recommended surgical procedure
    treatment_risks: str  # Known risks of the treatment
    treatment_benefits: str  # Benefits of the treatment
    prognosis_with_treatment: str  # Expected outcome with treatment
    prognosis_without_treatment: str  # Expected outcome without treatment


class RoundEvaluation(BaseModel):
    """Per-round evaluation results"""
    round_number: int  # Which round was evaluated
    
    # Criteria-based evaluation
    criteria_evaluations: list[CriterionEvaluation] = []  # Detailed criterion-by-criterion assessment
    
    # Calculated scores (0-1 scale: met_criteria / active_criteria)
    empathy_score: float  # Empathy criteria score (0-10 for backward compatibility)
    persuasion_score: float  # Persuasion criteria score (0-10 for backward compatibility)
    safety_score: float  # Safety criteria score (0-10 for backward compatibility)
    
    # Qualitative assessment
    patient_state_change: str  # Description of how patient's attitude changed
    should_stop: bool  # Whether dialogue should terminate
    stop_reason: str | None  # "patient_left" | "patient_accepted" | "max_rounds_reached" | null


class DialogueTurn(BaseModel):
    """Single turn in doctor-patient dialogue with per-round evaluation"""
    turn_number: int  # Sequential turn number in dialogue
    speaker: Literal["doctor", "patient"]  # Speaker identifier
    message: str  # Dialogue message content
    timestamp: str  # ISO 8601 timestamp
    round_evaluation: RoundEvaluation | None = None  # Evaluation results if round complete


class DialogueSession(BaseModel):
    """Complete dialogue session record with per-round evaluations"""
    session_id: str  # Unique session identifier
    persona_id: str  # Patient persona identifier
    doctor_agent_url: str  # Purple agent endpoint
    start_time: str  # ISO 8601 timestamp
    end_time: str | None = None  # ISO 8601 timestamp
    turns: list[DialogueTurn] = []  # All dialogue turns
    total_rounds: int = 0  # Number of complete rounds
    final_outcome: str | None = None  # "patient_accepted" | "patient_left" | "max_rounds_reached"
    stop_reason: str | None = None  # Why dialogue terminated


class PerformanceReport(BaseModel):
    """Comprehensive final report with per-round and overall scores"""
    session_id: str  # Reference to DialogueSession
    final_outcome: str  # "patient_accepted" | "patient_left" | "max_rounds_reached"
    total_rounds: int  # Number of rounds completed
    
    # Per-Round Breakdown
    round_scores: list[RoundEvaluation]  # Score for each round
    
    # Overall Aggregate Scores
    overall_empathy: float  # Mean empathy across all rounds (0-10)
    overall_persuasion: float  # Mean persuasion across all rounds (0-10)
    overall_safety: float  # Mean safety across all rounds (0-10)
    aggregate_score: float  # Weighted overall score (0-100)
    
    # Qualitative Analysis
    strengths: list[str]  # Identified strengths
    weaknesses: list[str]  # Identified weaknesses
    key_moments: list[str]  # Critical dialogue turns
    
    # Actionable Suggestions
    improvement_recommendations: list[str]  # Specific advice
    alternative_approaches: list[str]  # What could have been done differently
    
    # Summary
    evaluation_summary: str  # Overall text summary


class MedicalEvalResult(BaseModel):
    """Complete evaluation results across multiple personas"""
    assessment_id: str  # Unique assessment identifier
    doctor_agent_url: str  # Evaluated purple agent
    timestamp: str  # ISO 8601 timestamp
    sessions: list[DialogueSession]  # All dialogue sessions conducted
    reports: list[PerformanceReport]  # Comprehensive reports per session
    mean_aggregate_score: float  # Average score across all sessions
    overall_summary: str  # Text summary across all personas


# ==================== Agent Card Helpers ====================

def medical_judge_agent_card(agent_name: str, card_url: str) -> AgentCard:
    """Generate agent card for Medical Dialogue Judge"""
    skill = AgentSkill(
        id='evaluate_medical_dialogue',
        name='Evaluate medical dialogue agents',
        description='Orchestrate and evaluate doctor-patient dialogue across multiple patient personas with MBTI personality types.',
        tags=['medical', 'evaluation', 'dialogue'],
        examples=["""
{
  "participants": {
    "doctor": "http://127.0.0.1:9019"
  },
  "config": {
    "persona_ids": ["INTJ_M_PNEUMO", "ESFP_F_LUNG"],
    "max_rounds": 5
  }
}
""", """
{
  "participants": {
    "doctor": "http://127.0.0.1:9019"
  },
  "config": {
    "persona_ids": ["all"],
    "max_rounds": 5
  }
}
"""]
    )
    agent_card = AgentCard(
        name=agent_name,
        description='Evaluates doctor agents ability to persuade patients to accept surgical treatment across diverse patient personas (16 MBTI types × 2 genders × 2 medical conditions).',
        url=card_url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    return agent_card
