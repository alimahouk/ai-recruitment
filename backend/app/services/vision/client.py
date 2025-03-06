import time
from contextlib import contextmanager
from io import BytesIO
from threading import Lock
from typing import Optional

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from filelock import FileLock
from openai import AzureOpenAI
from PIL import Image

from backend.app.config import logger
from backend.app.exceptions import LLMInferenceError
from backend.app.services.vision.config import OpenAI4oConfig, VisionConfig
from backend.app.services.vision.models import ImageAnalysisResult
from backend.app.services.vision.types import CVDescription, WebpageDescription
from backend.app.services.vision.utils import encode_image


class VisionAnalysisClient:
    """Client for handling both Azure Vision and OpenAI vision analysis."""

    def __init__(
        self,
        vision_config: VisionConfig,
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

        self.vision_client = ImageAnalysisClient(
            endpoint=vision_config.endpoint,
            credential=AzureKeyCredential(vision_config.key),
        )

        # Add rate limiting
        self._openai_lock = Lock()
        self._vision_lock = Lock()
        self._last_openai_call = 0
        self._last_vision_call = 0
        self.openai_rate_limit = 0.5  # seconds between calls
        self.vision_rate_limit = 1.0  # seconds between calls

    def analyze_image(
        self, image_data: BytesIO
    ) -> Optional[ImageAnalysisResult]:
        try:
            self._wait_for_vision_rate_limit()

            with Image.open(image_data) as img:
                width, height = img.size
                if width < 50 or height < 50 or width > 16000 or height > 16000:
                    raise ValueError(
                        f"Invalid image dimensions: {width}x{height}"
                    )

                result = self.vision_client.analyze(
                    image_data=image_data.getvalue(),
                    visual_features=[
                        VisualFeatures.CAPTION,
                        VisualFeatures.READ,
                    ],
                )

                return ImageAnalysisResult(
                    caption=result.caption.text if result.caption else None,
                    detected_text=(
                        "\n".join(
                            line.text
                            for block in result.read.blocks
                            for line in block.lines
                        )
                        if result.read and result.read.blocks
                        else None
                    ),
                )

        except Exception as e:
            raise ValueError(f"Failed to analyze image: {str(e)}")

    @contextmanager
    def _file_access(self, filename: str):
        lock = FileLock(f"{filename}.lock")
        with lock:
            try:
                yield
            finally:
                if lock.is_locked:
                    lock.release()

    @classmethod
    def from_env(cls) -> "VisionAnalysisClient":
        """Create client using environment variables."""
        vision_config = VisionConfig.from_env()
        try:
            openai_config = OpenAI4oConfig.from_env()
        except ValueError:
            openai_config = None
        return cls(vision_config, openai_config)

    def describe_image_for_accessibility(self, filename: str) -> Optional[str]:
        """
        Get an accessibility-focused description of an image using Azure OpenAI.

        Args:
            filename: Path to the image file

        Returns:
            String containing the accessibility description

        Raises:
            ValueError: If OpenAI client is not configured or for API errors
        """
        if not filename:
            raise ValueError("Filename cannot be None or empty")

        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        try:
            base64_image = encode_image(filename)

            response = self.openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this screenshot like you would to someone who is visually impaired.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                model=self.openai_config.model,
            )
            return response.choices[0].message.content

        except Exception as e:
            raise LLMInferenceError(
                f"Failed to generate accessibility description: {str(e)}"
            )

    def describe_screenshot(
        self, filename: str
    ) -> Optional[WebpageDescription]:
        """
        Generate a structured description of a webpage screenshot that can be used
        for automated interaction.

        Args:
            filename: Path to the image file

        Returns:
            WebpageDescription object containing the structured description

        Raises:
            ValueError: If OpenAI client is not configured or for API errors
        """
        if not filename:
            raise ValueError("Filename cannot be None or empty")

        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        try:
            base64_image = encode_image(filename)
            completion = self.openai_client.beta.chat.completions.parse(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing webpage screenshots and describing them in a way that helps AI systems locate and interact with elements. Focus on precision in describing locations and interactive elements. Use clear, consistent terms for positions (top, bottom, left, right, center) and measurements.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this webpage screenshot and provide a structured description that can help locate and interact with elements.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                model=self.openai_config.model,
                response_format=WebpageDescription,
            )
            description = completion.choices[0].message

            if description.refusal:
                logger.warning(description.refusal)
            else:
                return description.parsed

        except Exception as e:
            raise LLMInferenceError(
                f"Failed to generate screenshot description: {str(e)}"
            )

    def describe_doc_pages(
        self, filenames: list[str]
    ) -> Optional[CVDescription]:
        """
        Generate an assessment for multiple CV page screenshots.

        Args:
            filenames: List of paths to image files

        Returns:
            A CVDescription object containing the structured assessment

        Raises:
            ValueError: If OpenAI client is not configured or for API errors
        """
        if not filenames:
            raise ValueError("Filenames list cannot be empty")

        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        try:
            # Create message content with all images
            content = [
                {
                    "type": "text",
                    "text": """# ASSIGNMENT

                    Analyze these CV screenshots and provide a structured assessment that can help a recruiter assess the personality and creativity of the candidate based on the design of their CV.
                    
                    ## RULES

                    * For all numerical scores, give a score **between 0 and 10**. **Do not** come up with your own scoring system.
                    * Be fair but also critical. Don't try to be nice or flattering. *This is very important* as you don't want to waste the recruiter or candidate's time.
                    * Observe all kinds of little details, e.g. does the document look like it was typeset using LaTeX? If so, that indicates the candidate is probably technically-inclined. Is there a relation between the styling of the document and the candidate's field? Pose such questions to yourself when assessing.
                    * **Do not** hallucinate.
                    * **Do not** make up factual information.""",
                }
            ]

            # Add each image to the content
            for filename in filenames:
                base64_image = encode_image(filename)
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    }
                )

            # Make single API call with all images
            completion = self.openai_client.beta.chat.completions.parse(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a recruitment assistant who is assessing the suitability of a candidate for a job based on their CV. You are given a list of screenshots of the candidate's CV. You need to describe the candidate's CV in a way that helps the recruiter assess the personality and creativity of the candidate based on the design of their CV.",
                    },
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
                model=self.openai_config.model,
                response_format=CVDescription,
                temperature=0,
            )
            description = completion.choices[0].message

            if description.refusal:
                logger.warning(description.refusal)
                return None

            return description.parsed

        except Exception as e:
            raise LLMInferenceError(
                f"Failed to generate document page descriptions: {str(e)}"
            )

    def _wait_for_vision_rate_limit(self):
        with self._vision_lock:
            now = time.time()
            if now - self._last_vision_call < self.vision_rate_limit:
                time.sleep(
                    self.vision_rate_limit - (now - self._last_vision_call)
                )
            self._last_vision_call = time.time()
