"""
Patient Constructor - Generates patient persona system prompts from templates

Flow:
1. Generate PatientBackground first (full background info including medical and personal details)
2. Use PatientBackground to construct patient simulator prompt
3. Extract PatientClinicalInfo from PatientBackground (subset for doctor - no extraction needed!)
"""

import logging
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from persona_manager import PersonaManager
from common import PatientPersona, PatientBackground, PatientClinicalInfo

logger = logging.getLogger(__name__)


class PatientConstructor:
    """Constructs patient system prompts from MBTI/gender/case templates
    
    New flow:
    1. Generate PatientBackground (full background) first
    2. Use background to construct patient simulator prompt
    3. PatientClinicalInfo is derived from PatientBackground (no LLM extraction needed)
    """
    
    def __init__(self, client: OpenAI, model: str, persona_manager: PersonaManager | None = None):
        """
        Initialize PatientConstructor
        
        Args:
            client: OpenAI client for LLM calls
            model: Model name to use
            persona_manager: PersonaManager instance (creates new if None)
        """
        self.client = client
        self.model = model
        self.persona_manager = persona_manager or PersonaManager()
    
    def construct_patient_persona(self, persona_id: str) -> tuple[PatientPersona, PatientBackground, PatientClinicalInfo]:
        """
        Generate complete patient persona with background and clinical info
        
        Flow:
        1. Parse persona_id to get MBTI, optional gender, and case
        2. Generate PatientBackground (full details including generated gender if needed)
        3. Build system prompt from background
        4. Derive PatientClinicalInfo from background (subset, no LLM call)
        
        Args:
            persona_id: e.g., "INTJ_PNEUMO" or "INTJ_M_PNEUMO"
        
        Returns:
            tuple: (PatientPersona, PatientBackground, PatientClinicalInfo)
        """
        logger.info(f"Constructing patient persona: {persona_id}")
        
        # Parse persona components (gender is optional)
        mbti, gender_code, case_code = self.persona_manager.parse_persona_id(persona_id)
        gender = None
        if gender_code:
            gender = "male" if gender_code == "M" else "female"
        medical_case = "pneumothorax" if case_code == "PNEUMO" else "lung_cancer"
        
        # Load prompt templates
        templates = self.persona_manager.load_prompt_templates(persona_id)
        
        # Step 1: Generate PatientBackground first
        background = self._generate_patient_background(
            mbti_prompt=templates["mbti"],
            gender_prompt=templates.get("gender"),  # May be None
            case_prompt=templates["case"],
            mbti_type=mbti,
            gender=gender,
            medical_case=medical_case
        )
        
        # Step 2: Build system prompt from background
        system_prompt = self._build_system_prompt_from_background(
            background=background,
            mbti_prompt=templates["mbti"],
            mbti_type=mbti
        )
        
        # Step 3: Create PatientPersona
        persona = PatientPersona(
            persona_id=persona_id,
            mbti_type=mbti,
            gender=background.gender,  # Use generated gender from background
            medical_case=medical_case,
            system_prompt=system_prompt
        )
        
        # Step 4: Derive PatientClinicalInfo from background (no LLM extraction!)
        clinical_info = self._derive_clinical_info(background, include_gender=(gender is not None))
        
        logger.info(f"Successfully constructed persona: {persona_id}")
        return persona, background, clinical_info
    
    def _generate_patient_background(
        self,
        mbti_prompt: str,
        gender_prompt: str | None,
        case_prompt: str,
        mbti_type: str,
        gender: str | None,
        medical_case: str
    ) -> PatientBackground:
        """
        Generate full patient background using LLM
        
        Args:
            mbti_prompt: MBTI personality description
            gender_prompt: Gender context (may be None if gender not specified)
            case_prompt: Medical case details
            mbti_type: MBTI type code
            gender: male/female or None (will be generated if None)
            medical_case: pneumothorax/lung_cancer
        
        Returns:
            PatientBackground with all details
        """
        gender_instruction = ""
        if gender:
            gender_instruction = f"Gender is specified as: {gender}"
            if gender_prompt:
                gender_instruction += f"\nGender context:\n{gender_prompt}"
        else:
            gender_instruction = "Gender is NOT specified. You should randomly choose male or female and generate appropriate background."
        
        system_msg = """You are generating a complete patient background for a medical dialogue simulation.

Generate a realistic, detailed patient profile that includes:
1. Demographics (age 35-65, gender, occupation aligned with MBTI)
2. Complete medical information (symptoms, diagnosis, treatment details, prognosis)
3. Personal background (family, lifestyle, values, concerns)

The patient background must be:
- Medically accurate and realistic
- Consistent with the MBTI personality type
- Cohesive and believable as a real person

Return a structured JSON object with ALL required fields filled in with realistic, detailed content."""

        user_msg = f"""Generate a complete patient background by combining these elements:

=== MBTI Personality Type: {mbti_type} ===
{mbti_prompt}

=== Gender ===
{gender_instruction}

=== Medical Case: {medical_case} ===
{case_prompt}

Generate a complete PatientBackground with:
- age: int (35-65, realistic for condition)
- gender: str ("male" or "female")
- occupation: str (job aligned with personality)
- medical_case: str ("{medical_case}")
- symptoms: str (current symptoms patient experiences)
- diagnosis: str (medical diagnosis)
- recommended_treatment: str (surgical procedure recommended)
- treatment_risks: str (risks of the treatment)
- treatment_benefits: str (benefits of treatment)
- prognosis_with_treatment: str (expected outcome if treated)
- prognosis_without_treatment: str (expected outcome if not treated)
- family_situation: str (family context)
- lifestyle: str (daily life, habits)
- values: str (what matters to this person)
- concerns_and_fears: str (personality-driven concerns about the medical situation)"""

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                ChatCompletionSystemMessageParam(content=system_msg, role="system"),
                ChatCompletionUserMessageParam(content=user_msg, role="user"),
            ],
            response_format=PatientBackground,
        )
        
        background = completion.choices[0].message.parsed
        logger.info(f"Generated patient background: age={background.age}, gender={background.gender}, occupation={background.occupation}")
        return background
    
    def _build_system_prompt_from_background(
        self,
        background: PatientBackground,
        mbti_prompt: str,
        mbti_type: str
    ) -> str:
        """
        Build patient simulator system prompt from generated background
        
        Args:
            background: Generated PatientBackground
            mbti_prompt: MBTI personality description
            mbti_type: MBTI type code
        
        Returns:
            System prompt for patient agent
        """
        system_msg = """You are creating a patient roleplay system prompt from structured background information.

Your task: Transform the patient background data into a compelling, second-person narrative that will instruct an AI to roleplay this patient.

Write in SECOND PERSON ("You are...") as direct instructions to roleplay this character.
The prompt should:
- Establish the character's identity, background, and current situation
- Describe their personality and communication style based on MBTI
- Detail their medical situation and concerns
- Explain how they respond to doctors and medical discussions

Output 300-500 words of cohesive narrative."""

        user_msg = f"""Transform this patient background into a roleplay system prompt:

=== MBTI Type: {mbti_type} ===
{mbti_prompt}

=== Patient Background ===
Age: {background.age}
Gender: {background.gender}
Occupation: {background.occupation}

Medical Situation:
- Case: {background.medical_case}
- Symptoms: {background.symptoms}
- Diagnosis: {background.diagnosis}
- Recommended Treatment: {background.recommended_treatment}
- Treatment Risks: {background.treatment_risks}
- Treatment Benefits: {background.treatment_benefits}
- Prognosis with Treatment: {background.prognosis_with_treatment}
- Prognosis without Treatment: {background.prognosis_without_treatment}

Personal Background:
- Family: {background.family_situation}
- Lifestyle: {background.lifestyle}
- Values: {background.values}
- Concerns and Fears: {background.concerns_and_fears}

Write a cohesive patient persona in second person ("You are...") that brings this character to life."""

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                ChatCompletionSystemMessageParam(content=system_msg, role="system"),
                ChatCompletionUserMessageParam(content=user_msg, role="user"),
            ],
        )
        
        system_prompt = completion.choices[0].message.content
        
        # Add explicit roleplay instructions
        roleplay_footer = """

---
ROLEPLAY INSTRUCTIONS:
You are roleplaying this patient character in a medical consultation with a doctor. Stay fully in character throughout the entire conversation. Respond naturally as this patient would, expressing their concerns, asking questions, and reacting to the doctor's explanations based on your personality, background, and medical situation. Do not break character or discuss the roleplay itself."""
        
        return system_prompt + roleplay_footer
    
    def _derive_clinical_info(self, background: PatientBackground, include_gender: bool = True) -> PatientClinicalInfo:
        """
        Derive PatientClinicalInfo from PatientBackground (NO LLM call needed!)
        
        This is a simple extraction of clinical fields that a doctor would have access to.
        Does NOT include: symptoms (patient reports), personality, concerns, lifestyle.
        
        Args:
            background: PatientBackground with full details
            include_gender: Whether to include gender in clinical info (for privacy)
        
        Returns:
            PatientClinicalInfo (subset of background for doctor)
        """
        return PatientClinicalInfo(
            age=background.age,
            gender=background.gender if include_gender else None,
            medical_case=background.medical_case,
            diagnosis=background.diagnosis,
            recommended_treatment=background.recommended_treatment,
            treatment_risks=background.treatment_risks,
            treatment_benefits=background.treatment_benefits,
            prognosis_with_treatment=background.prognosis_with_treatment,
            prognosis_without_treatment=background.prognosis_without_treatment
        )
