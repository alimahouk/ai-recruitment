import time
from threading import Lock
from typing import Optional

from openai import AzureOpenAI

from backend.app.config import logger
from backend.app.exceptions import LLMInferenceError
from backend.app.services.llm.types import CVProfile, RoleProfile
from backend.app.services.vision.config import OpenAI4oConfig
from backend.app.services.vision.types import CVDescription

INDUSTRIES = frozenset(
    {
        "Accounting",
        "Aerospace",
        "Agriculture",
        "Artificial Intelligence",
        "Automotive",
        "Banking",
        "Biotechnology",
        "Chemical",
        "Construction",
        "Consulting",
        "Consumer Goods",
        "Defense",
        "Education",
        "Energy",
        "Entertainment",
        "Environmental",
        "Fashion",
        "Financial Services",
        "Food & Beverage",
        "Gaming",
        "Government",
        "Healthcare",
        "Hospitality",
        "Industrial Manufacturing",
        "Information Technology",
        "Insurance",
        "Legal",
        "Logistics",
        "Marketing",
        "Media",
        "Mining",
        "Non-Profit",
        "Oil & Gas",
        "Pharmaceutical",
        "Real Estate",
        "Retail",
        "Software",
        "Sports",
        "Telecommunications",
        "Transportation",
        "Travel",
        "Utilities",
    }
)


class LLMProcessor:
    """Handles LLM processing of CV content"""

    def __init__(
        self,
        openai_config: Optional[OpenAI4oConfig] = None,
    ):
        self.openai_client = None
        self.openai_config = openai_config
        if openai_config:
            self.openai_client = AzureOpenAI(
                api_key=openai_config.api_key,
                api_version=openai_config.api_version,
                azure_endpoint=openai_config.endpoint,
            )

        # Add rate limiting
        self._api_rate_limit = 0.5  # seconds between calls
        self._last_api_call = 0
        self._lock = Lock()

    @classmethod
    def from_env(cls) -> "LLMProcessor":
        """Create a client using environment variables."""
        try:
            openai_config = OpenAI4oConfig.from_env()
        except ValueError:
            openai_config = None
        return cls(openai_config)

    def _wait_for_rate_limit(self):
        """Enforce rate limiting for API calls"""
        with self._lock:
            now = time.time()
            if now - self._last_api_call < self._api_rate_limit:
                time.sleep(self._api_rate_limit - (now - self._last_api_call))
            self._last_api_call = time.time()

    def analyze_cv(
        self, paragraphs: list[str], creativity_assessment: CVDescription
    ) -> Optional[CVProfile]:
        """Process CV paragraphs and creativity assessment to generate structured profile"""

        try:
            self._wait_for_rate_limit()  # Add rate limiting

            content = "\n".join(paragraphs)
            completion = self.openai_client.beta.chat.completions.parse(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert CV analyzer. Extract key information and provide structured insights.",
                    },
                    {
                        "role": "user",
                        "content": f"""# ASSIGNMENT

                        Analyze the following CV content and create a structured profile. 

                        ## RULES
                        
                        * Consider both the content and the creativity assessment in your analysis.
                        * Be fair but also critical. Don't try to be nice or flattering. *This is very important* as you don't want to waste the recruiter or candidate's time.
                        * For unprovided information, populate the field with an empty string.
                        * For unprovided dates, populate the field with `0`.
                        * For date ranges, populate the field with `0` when it represents the present day. e.g. if a job role's date range is "2020-01-01 to present", populate the start date's month and year but for the end date, populate the month and year with `0`.
                        * The outer-most `summary` can be your own concise summary of the entire CV content. Use the third-person perspective.
                        * For role-specific summaries, use the third-person perspective and make sure to include any key information (e.g. company names, projects, etc.)
                        * `highlights` can be a list of the most notable points about the candidate.
                        * For `nationality` or any `country` fields, use the ISO 3166-1 alpha-2 code of the country.
                        * For `spoken_languages`, use the ISO 639-1 language code of each language. If no spoken languages are explicitly provided, populate the field with the language of the CV content.
                        * For `industries`, select up to three industries that best fit the candidate's experience from the given list of industries. You don't have to select all three if less than three industries are relevant, but three is the maximum.
                        * Determine `industries` before `level`, then use the industries to judge what level the candidate is at. Be fair and don't be too generous with the seniority level.
                        * **Do not** hallucinate.
                        * **Do not** make up factual information.

                        CV Content:
                        {content}

                        Creativity Assessment:
                        {creativity_assessment}

                        ### INDUSTRIES
                        {INDUSTRIES}""",
                    },
                ],
                model=self.openai_config.model,
                response_format=CVProfile,
                temperature=0,
            )

            if completion.choices[0].message.refusal:
                logger.warning(completion.choices[0].message.refusal)
                return None

            return completion.choices[0].message.parsed

        except Exception as e:
            raise LLMInferenceError(f"Failed to analyze CV: {str(e)}")

    def analyze_jd(self, paragraphs: list[str]) -> Optional[RoleProfile]:
        """Process CV paragraphs and creativity assessment to generate structured profile"""

        try:
            self._wait_for_rate_limit()  # Add rate limiting

            content = "\n".join(paragraphs)
            completion = self.openai_client.beta.chat.completions.parse(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert job description analyzer. Extract key information and provide structured insights.",
                    },
                    {
                        "role": "user",
                        "content": f"""# ASSIGNMENT

                        Analyze the following job description content and create a structured listing. 

                        ## RULES
                        
                        * For unprovided information, populate the field with an empty string.
                        * For unprovided dates, populate the field with `0`.
                        * For date ranges, populate the field with `0` when it represents the present day. e.g. if a job role's date range is "2020-01-01 to present", populate the start date's month and year but for the end date, populate the month and year with `0`.
                        * For any `country` fields, use the ISO 3166-1 alpha-2 code of the country.
                        * For `industries`, select up to three industries that best fit the candidate's experience from the given list of industries. You don't have to select all three if less than three industries are relevant, but three is the maximum.
                        * **Do not** hallucinate.
                        * **Do not** make up factual information.

                        Job Description Content:
                        {content}

                        ### INDUSTRIES
                        {INDUSTRIES}""",
                    },
                ],
                model=self.openai_config.model,
                response_format=RoleProfile,
                temperature=0,
            )

            if completion.choices[0].message.refusal:
                logger.warning(completion.choices[0].message.refusal)
                return None

            return completion.choices[0].message.parsed

        except Exception as e:
            raise LLMInferenceError(f"Failed to analyze CV: {str(e)}")
