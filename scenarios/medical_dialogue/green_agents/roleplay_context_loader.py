"""
Role-play Context Loader - Loads and formats context engineering templates

This module loads role-play priming context from CSV files to improve
agent performance in character role-playing tasks.
"""

import csv
import logging
from pathlib import Path
from typing import List, Union, Dict

from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

logger = logging.getLogger(__name__)


class RolePlayContextLoader:
    """Loads and formats role-play context from CSV files"""
    
    def __init__(self, context_dir: Path | str):
        """
        Initialize context loader
        
        Args:
            context_dir: Path to directory containing context CSV files
        """
        self.context_dir = Path(context_dir)
        logger.info(f"RolePlayContextLoader initialized with context_dir: {self.context_dir}")
    
    def load_roleplay_template(self, filename: str = "role_play.csv") -> List[Dict[str, str]]:
        """
        Load role-play template from CSV
        
        Args:
            filename: Name of CSV file in context_dir
        
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        filepath = self.context_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Role-play template not found: {filepath}")
            return []
        
        messages = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                role = row.get('Role', '').strip().upper()
                message = row.get('Message', '').strip()
                
                # Map USER/ASSISTANT to OpenAI chat roles
                if role == 'USER':
                    messages.append({'role': 'user', 'content': message})
                elif role == 'ASSISTANT':
                    messages.append({'role': 'assistant', 'content': message})
                else:
                    logger.warning(f"Unknown role in CSV: {role}")
        
        logger.info(f"Loaded {len(messages)} role-play context messages from {filename}")
        return messages
    
    def format_roleplay_context(
        self,
        role_core_description: str,
        role_acknowledgement_phrase: str,
        role_rules_and_constraints: str,
        role_confirmation_phrase: str,
        example_say: str,
        example_think: str,
        example_do: str
    ) -> tuple[str, List[Union[ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam]]]:
        """
        Format complete role-play context from template
        
        This is a simple template filler - all content should be provided by caller.
        Does NOT make assumptions about the role.
        
        Args:
            role_core_description: Detailed character description (goes in USER message)
            role_acknowledgement_phrase: Acknowledgement after receiving core description
            role_rules_and_constraints: Rules and constraints for the role
            role_confirmation_phrase: Confirmation after receiving rules
            example_say: Example dialogue
            example_think: Example inner thoughts
            example_do: Example actions
        
        Returns:
            Tuple of (simple_system_prompt, list of context messages)
        """
        template_messages = self.load_roleplay_template()
        
        if not template_messages:
            logger.warning("No template messages loaded, returning empty context")
            raise RuntimeError("Role-play template messages could not be loaded.")
        
        # Replace placeholders in the template
        formatted_messages = []
        
        for msg in template_messages:
            content = msg['content']
            
            # Replace all placeholders with provided values
            replacements = {
                '{ROLE_CORE_DESCRIPTION}': role_core_description,
                '{ROLE_ACKNOWLEDGEMENT_PHRASE}': role_acknowledgement_phrase,
                '{ROLE_RULES_AND_CONSTRAINTS}': role_rules_and_constraints,
                '{ROLE_CONFIRMATION_PHRASE}': role_confirmation_phrase,
                '{EXAMPLE_SAY}': example_say,
                '{EXAMPLE_THINK}': example_think,
                '{EXAMPLE_DO}': example_do
            }
            
            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)
            
            # Create type-safe message params
            if msg['role'] == 'user':
                formatted_messages.append(ChatCompletionUserMessageParam(
                    content=content,
                    role='user'
                ))
            elif msg['role'] == 'assistant':
                formatted_messages.append(ChatCompletionAssistantMessageParam(
                    content=content,
                    role='assistant'
                ))
        
        # Create simple system prompt for roleplay mode
        simple_system_prompt = "You are participating in a roleplay. Follow the instructions provided in the conversation history to play your assigned role."
        
        logger.info(f"Formatted {len(formatted_messages)} role-play context messages")
        return simple_system_prompt, formatted_messages
