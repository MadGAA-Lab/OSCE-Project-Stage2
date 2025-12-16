"""
Patient Agent - Simulates patient with personality-driven behavior
"""

import logging
import random
import time
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, \
    ChatCompletionAssistantMessageParam

from roleplay_context_loader import RolePlayContextLoader
from common import PatientRoleplayExamples

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def extract_spoken_dialogue(response: str) -> str:
    """
    Extract spoken dialogue and visible actions from a roleplay response.
    
    The patient may respond in format: "Say: ... Think: ... Do: ..."
    We hide "Think:" (internal thoughts) but keep "Say:" and "Do:" (visible to doctor).
    
    Args:
        response: Full response from patient agent
    
    Returns:
        Spoken dialogue and visible actions (what the doctor can see/hear)
    """
    # Check if response follows the Say/Think/Do format
    if "Think:" in response:
        # Remove the Think: section (internal thoughts hidden from doctor)
        parts = response.split("Think:")
        before_think = parts[0]  # Say: and possibly Do: before Think:
        
        # Check if there's a Do: section after Think:
        if len(parts) > 1 and "Do:" in parts[1]:
            after_think = "Do:" + parts[1].split("Do:")[1]
            return (before_think + after_think).strip()
        
        return before_think.strip()
    
    # If no Think: section, return the whole response (Say: and Do: are both visible)
    return response.strip()

# Diverse fallback messages when API fails - natural patient responses
FALLBACK_MESSAGES = [
    "Sorry, what were you saying? I zoned out for a second there.",
    "Wait, can you repeat that? I'm having trouble focusing right now.",
    "I... I'm not sure what to say to that.",
    "Hold on, I need to think about this for a moment.",
    "I'm sorry, my mind is just racing right now.",
    "Can we slow down? This is a lot to process.",
    "I don't know... I'm really confused about all this.",
    "Everything you're saying is just... it's overwhelming.",
]


class PatientAgent:
    """
    Simulates patient with personality-driven behavior
    
    Uses full system prompt (MBTI personality + background + concerns)
    that is HIDDEN from Doctor Agent
    """
    
    def __init__(
        self, 
        client: OpenAI, 
        model: str, 
        character_description: str, 
        max_retries: int = MAX_RETRIES, 
        retry_delay: int = RETRY_DELAY,
        use_roleplay_context: bool = True,
        roleplay_examples: Optional[PatientRoleplayExamples] = None,
        context_dir: Optional[Path | str] = None
    ):
        """
        Initialize PatientAgent
        
        Args:
            client: OpenAI client for LLM calls
            model: Model name to use
            character_description: Full patient character description (includes personality)
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            use_roleplay_context: Whether to use roleplay context engineering
            roleplay_examples: Generated roleplay examples from PatientConstructor
            context_dir: Path to agent_context directory (auto-detected if None)
        """
        self.client = client
        self.model = model
        self.character_description = character_description
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.dialogue_history: list[dict] = []  # List of {role: str, content: str}
        
        # Role-play context engineering
        self.use_roleplay_context = use_roleplay_context
        self.roleplay_system_prompt: str | None = None  # Simple system prompt for roleplay
        self.roleplay_context_messages: List[
            ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam
        ] = []
        
        if self.use_roleplay_context and roleplay_examples:
            # Auto-detect context_dir if not provided
            if context_dir is None:
                # Assume we're in green_agents/ and need to go up to medical_dialogue/agent_context
                context_dir = Path(__file__).parent.parent / "agent_context"
            
            context_loader = RolePlayContextLoader(context_dir)
            self.roleplay_system_prompt, self.roleplay_context_messages = context_loader.format_roleplay_context(
                role_core_description=roleplay_examples.role_core_description,
                role_acknowledgement_phrase=roleplay_examples.role_acknowledgement_phrase,
                role_rules_and_constraints=roleplay_examples.role_rules_and_constraints,
                role_confirmation_phrase=roleplay_examples.role_confirmation_phrase,
                example_say=roleplay_examples.example_say,
                example_think=roleplay_examples.example_think,
                example_do=roleplay_examples.example_do
            )
            logger.info(f"PatientAgent initialized with {len(self.roleplay_context_messages)} role-play context messages and simple system prompt")
        else:
            logger.info(f"PatientAgent initialized without role-play context")
        
        logger.info(f"PatientAgent initialized with personality-driven system prompt (retries={max_retries}, delay={retry_delay}s)")
    
    def reset(self):
        """Reset dialogue history for new conversation"""
        self.dialogue_history = []
        logger.info("PatientAgent dialogue history reset")
    
    def respond(self, doctor_message: str) -> str:
        """
        Generate patient response to doctor's message
        
        Uses LLM with personality traits to generate response.
        
        Args:
            doctor_message: Doctor's latest message
        
        Returns:
            Patient's response message
        """
        logger.info(f"Patient generating response to doctor message")
        
        # Add doctor's message to history
        self.dialogue_history.append({
            "role": "user",  # Doctor is "user" from patient's perspective
            "content": doctor_message
        })
        
        # Build conversation messages for LLM
        messages: List[
            ChatCompletionSystemMessageParam |
            ChatCompletionUserMessageParam |
            ChatCompletionAssistantMessageParam
        ] = []
        
        # Use simple system prompt if roleplay context is enabled, otherwise use full character description
        if self.use_roleplay_context and self.roleplay_system_prompt:
            messages.append(ChatCompletionSystemMessageParam(content=self.roleplay_system_prompt, role="system"))
            # Add role-play context priming messages (contains detailed character description)
            messages.extend(self.roleplay_context_messages)
        else:
            # Use full detailed character description as system prompt (backward compatibility)
            messages.append(ChatCompletionSystemMessageParam(content=self.character_description, role="system"))
        
        # Add dialogue history
        for turn in self.dialogue_history:
            if turn["role"] == "user":
                messages.append(ChatCompletionUserMessageParam(
                    content=turn["content"],
                    role="user"
                ))
            elif turn["role"] == "assistant":
                messages.append(ChatCompletionAssistantMessageParam(
                    content=turn["content"],
                    role="assistant"
                ))
        
        # Generate patient response with retry logic
        patient_response = None
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Generating patient response (attempt {attempt + 1}/{self.max_retries})")
                
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                
                patient_response = completion.choices[0].message.content
                
                # Check if response is valid
                if patient_response is not None and len(patient_response.strip()) > 0:
                    logger.info(f"Patient generated response ({len(patient_response)} chars)")
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1}: API returned empty or None content")
                    last_error = "Empty or None response from API"
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                last_error = str(e)
                
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        
        # Handle final failure
        if patient_response is None or len(patient_response.strip()) == 0:
            error_msg = f"Failed to generate patient response after {self.max_retries} attempts. Last error: {last_error}"
            logger.error(error_msg)
            # Use a random fallback message to maintain natural conversation flow
            patient_response = random.choice(FALLBACK_MESSAGES)
            logger.info(f"Using fallback message: {patient_response[:50]}...")
        
        # Log full response (including Think/Do if present) for debugging
        logger.debug(f"Full patient response: {patient_response[:200]}...")
        
        # IMPORTANT: Add patient's FULL response to history (including Think:)
        # This maintains complete internal context for the patient agent in future rounds
        # The patient can reference their own thoughts across the conversation
        self.dialogue_history.append({
            "role": "assistant",
            "content": patient_response  # Full response with Say:, Think:, and Do:
        })
        
        # Extract visible parts only (Say: + Do:, but NOT Think:)
        # This is what gets sent to the doctor - they cannot see internal thoughts
        spoken_dialogue = extract_spoken_dialogue(patient_response)
        logger.info(f"Visible response to doctor: {spoken_dialogue[:100]}...")
        
        return spoken_dialogue  # Doctor only receives this (no Think: part)
    
    def get_dialogue_history(self) -> list[dict]:
        """
        Get full dialogue history
        
        Returns:
            List of dialogue turns with role and content
        """
        return self.dialogue_history.copy()
