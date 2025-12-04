"""
Persona Manager - Utility to load prompt templates for patient personas
"""

import os
import random
from pathlib import Path


# All 16 MBTI types
MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP"
]

GENDERS = ["male", "female"]
MEDICAL_CASES = ["pneumothorax", "lung_cancer"]


class PersonaManager:
    """Manages prompt template files for patient personas"""
    
    def __init__(self, prompts_dir: str | None = None):
        """
        Initialize PersonaManager
        
        Args:
            prompts_dir: Path to prompts directory. If None, uses default location
        """
        if prompts_dir is None:
            # Default: scenarios/medical_dialogue/prompts/
            current_file = Path(__file__)
            scenario_dir = current_file.parent.parent
            self.prompts_dir = scenario_dir / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        self.mbti_dir = self.prompts_dir / "mbti"
        self.gender_dir = self.prompts_dir / "gender"
        self.cases_dir = self.prompts_dir / "cases"
    
    def parse_persona_id(self, persona_id: str) -> tuple[str, str | None, str]:
        """
        Parse persona_id into components
        
        Supports two formats:
        - With gender: "INTJ_M_PNEUMO" or "ESFP_F_LUNG"
        - Without gender: "INTJ_PNEUMO" or "ESFP_LUNG"
        
        Args:
            persona_id: e.g., "INTJ_M_PNEUMO", "ESFP_F_LUNG", "INTJ_PNEUMO"
        
        Returns:
            tuple: (mbti_type, gender_code or None, case_code)
        """
        parts = persona_id.split("_")
        
        if len(parts) == 3:
            # Format with gender: MBTI_GENDER_CASE
            mbti, gender_code, case_code = parts
            
            # Validate gender
            if gender_code.upper() not in ["M", "F"]:
                raise ValueError(f"Invalid gender code: {gender_code}. Use M or F")
            gender_code = gender_code.upper()
            
        elif len(parts) == 2:
            # Format without gender: MBTI_CASE
            mbti, case_code = parts
            gender_code = None
            
        else:
            raise ValueError(f"Invalid persona_id format: {persona_id}. Expected MBTI_GENDER_CASE or MBTI_CASE")
        
        # Validate MBTI
        if mbti.upper() not in MBTI_TYPES:
            raise ValueError(f"Invalid MBTI type: {mbti}")
        
        # Validate case
        if case_code.upper() not in ["PNEUMO", "LUNG"]:
            raise ValueError(f"Invalid case code: {case_code}. Use PNEUMO or LUNG")
        
        return mbti.upper(), gender_code, case_code.upper()
    
    def get_prompt_paths(self, persona_id: str) -> dict[str, Path | None]:
        """
        Get file paths for all prompt templates for a persona
        
        Args:
            persona_id: e.g., "INTJ_M_PNEUMO" or "INTJ_PNEUMO"
        
        Returns:
            dict with keys: 'mbti', 'gender' (may be None), 'case'
        """
        mbti, gender_code, case_code = self.parse_persona_id(persona_id)
        
        # Map codes to filenames
        case = "pneumothorax" if case_code == "PNEUMO" else "lung_cancer"
        
        paths = {
            "mbti": self.mbti_dir / f"{mbti.lower()}.txt",
            "case": self.cases_dir / f"{case}.txt"
        }
        
        # Gender is optional
        if gender_code:
            gender = "male" if gender_code == "M" else "female"
            paths["gender"] = self.gender_dir / f"{gender}.txt"
        else:
            paths["gender"] = None
        
        return paths
    
    def load_prompt_templates(self, persona_id: str) -> dict[str, str | None]:
        """
        Load all prompt templates for a persona
        
        Args:
            persona_id: e.g., "INTJ_M_PNEUMO" or "INTJ_PNEUMO"
        
        Returns:
            dict with keys: 'mbti', 'gender' (may be None), 'case' containing prompt text
        """
        paths = self.get_prompt_paths(persona_id)
        prompts = {}
        
        for key, path in paths.items():
            if path is None:
                prompts[key] = None
                continue
                
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                prompts[key] = f.read().strip()
        
        return prompts
    
    def get_all_persona_ids(self, include_gender: bool = True) -> list[str]:
        """
        Generate all possible persona IDs
        
        Args:
            include_gender: If True, generates 64 combinations (MBTI × gender × case)
                           If False, generates 32 combinations (MBTI × case)
        
        Returns:
            list of all persona_ids
        """
        persona_ids = []
        for mbti in MBTI_TYPES:
            for case_code in ["PNEUMO", "LUNG"]:
                if include_gender:
                    for gender_code in ["M", "F"]:
                        persona_ids.append(f"{mbti}_{gender_code}_{case_code}")
                else:
                    persona_ids.append(f"{mbti}_{case_code}")
        return persona_ids
    
    def expand_persona_ids(self, persona_ids: list[str]) -> list[str]:
        """
        Expand persona_ids list, handling "all", "all_no_gender", and "random" keywords
        
        Args:
            persona_ids: List that may contain special keywords or specific persona IDs
                - "all": All 64 combinations (with gender)
                - "all_no_gender": All 32 combinations (without gender)
                - "random": One random persona (with gender)
                - "random_no_gender": One random persona (without gender)
        
        Returns:
            Expanded list of specific persona IDs
        """
        if "all" in persona_ids:
            return self.get_all_persona_ids(include_gender=True)
        if "all_no_gender" in persona_ids:
            return self.get_all_persona_ids(include_gender=False)
        if "random" in persona_ids:
            mbti = random.choice(MBTI_TYPES)
            gender_code = random.choice(["M", "F"])
            case_code = random.choice(["PNEUMO", "LUNG"])
            return [f"{mbti}_{gender_code}_{case_code}"]
        if "random_no_gender" in persona_ids:
            mbti = random.choice(MBTI_TYPES)
            case_code = random.choice(["PNEUMO", "LUNG"])
            return [f"{mbti}_{case_code}"]
        return persona_ids
