import logging
import threading
from datetime import datetime
from queue import Empty, Queue
from typing import Optional

from devtools import pprint

from backend.app.exceptions import log_exception
from backend.app.services.llm.processor import LLMProcessor
from backend.app.services.llm.types import Employment
from backend.app.services.users.cv_profile_manager import CVProfileManager
from backend.app.services.users.user_manager import UserManager
from backend.app.services.vision.types import CVDescription

logger = logging.getLogger(__name__)


class ProfilerWorker:
    """Worker class for processing analyzed CV paragraphs and creating profiles."""

    _instance: Optional["ProfilerWorker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ProfilerWorker, cls).__new__(cls)
            return cls._instance

    def __init__(self, num_workers: int = 2):
        # Only initialize once
        if not hasattr(self, "initialized"):
            self.profile_queue: Queue[tuple[str, list[str], CVDescription]] = (
                Queue()
            )
            self.is_running = True
            self.workers: list[threading.Thread] = []
            self.llm_processor = LLMProcessor.from_env()

            # Create multiple worker threads
            for i in range(num_workers):
                worker = threading.Thread(
                    target=self._process_queue,
                    name=f"Profiler-{i}",
                    daemon=True,
                )
                self.workers.append(worker)
                worker.start()
                logger.info(f"Started profiler thread {worker.name}")

            self.initialized = True

    def add_to_queue(
        self,
        cv_id: str,
        paragraphs: list[str],
        creativity_assessment: CVDescription,
    ) -> None:
        """Add analyzed CV paragraphs to the processing queue."""
        self.profile_queue.put((cv_id, paragraphs, creativity_assessment))
        logger.info(f"Added CV {cv_id} to profiling queue")

    def _calculate_average_tenure(
        self, employment_history: list[Employment]
    ) -> float:
        """Calculate average duration (in months) spent in each role.

        Args:
            employment_history: List of Employment records

        Returns:
            float: Average months per role, rounded to nearest whole month
        """
        if not employment_history:
            return 0.0

        total_months = 0

        for employment in employment_history:
            # Get start date
            start_year = employment.start_date.year
            start_month = employment.start_date.month

            # Get end date - if year is 0, it means present day
            end_year = employment.end_date.year
            end_month = employment.end_date.month

            if end_year == 0:  # Current role
                now = datetime.now()
                end_year = now.year
                end_month = now.month

            # Calculate total months
            months = (end_year - start_year) * 12 + (end_month - start_month)
            total_months += months

        # Calculate average and round to nearest month
        return round(total_months / len(employment_history))

    def _calculate_years_experience(
        self, employment_history: list[Employment]
    ) -> float:
        """Calculate total years of experience from employment history.

        Args:
            employment_history: List of Employment records

        Returns:
            float: Total years of experience, rounded to nearest 0.5 years
        """
        total_years = 0.0

        for employment in employment_history:
            # Get start date
            start_year = employment.start_date.year
            start_month = employment.start_date.month

            # Get end date - if year is 0, it means present day
            end_year = employment.end_date.year
            end_month = employment.end_date.month

            if end_year == 0:  # Current role
                now = datetime.now()
                end_year = now.year
                end_month = now.month

            # Calculate years including months (as decimal)
            years = end_year - start_year
            months = end_month - start_month
            total_years += years + (months / 12)

        # Round to nearest 0.5
        return round(total_years * 2) / 2

    def _process_queue(self) -> None:
        """Worker thread that processes analyzed CV paragraphs from the queue."""
        thread_name = threading.current_thread().name
        logger.info(f"Profiler {thread_name} started")

        while self.is_running:
            try:
                # Block for 1 second before checking is_running again
                cv_id, paragraphs, creativity_assessment = (
                    self.profile_queue.get(timeout=1)
                )

                try:
                    logger.info(f"Profiler {thread_name} processing CV {cv_id}")

                    # Process CV content using LLM
                    profile = self.llm_processor.analyze_cv(
                        paragraphs=paragraphs,
                        creativity_assessment=creativity_assessment,
                    )

                    # Calculate years of experience
                    average_tenure: Optional[float] = None
                    years_experience: Optional[float] = None
                    if profile and profile.employment_history:
                        years_experience = self._calculate_years_experience(
                            profile.employment_history
                        )
                        average_tenure = self._calculate_average_tenure(
                            profile.employment_history
                        )

                    logger.info(f"Generated profile for CV {cv_id}")
                    pprint(creativity_assessment)
                    pprint(profile)
                    logger.info(
                        f"Total years of experience: {years_experience} years"
                    )
                    logger.info(f"Average tenure: {average_tenure} months")

                    cv_profile_manager = CVProfileManager()
                    cv_profile_manager.update_cv_profile(
                        cv_id,
                        profile,
                        average_tenure=average_tenure,
                        creativity_score=creativity_assessment.creativity_score,
                        formatting_score=creativity_assessment.formatting_score,
                        grammar_score=creativity_assessment.grammar_score,
                        years_experience=years_experience,
                    )
                    user_manager = UserManager()
                    user = user_manager.get_user_by_id(cv_id)
                    if user:
                        cv_profile_run = cv_profile_manager.get_cv_profile(
                            cv_id
                        )
                        user = user_manager.update_user_from_cv_profile(
                            cv_id, cv_profile_run
                        )
                        if not user.is_onboarded:
                            user.is_onboarded = True
                            user_manager.update_user(cv_id, user)

                    logger.info(
                        f"Profiler {thread_name} successfully processed CV {cv_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Profiler {thread_name} encountered an error processing CV {cv_id}: {str(e)}"
                    )

                finally:
                    # Mark task as done even if it failed
                    self.profile_queue.task_done()

            except Empty:
                # This is expected when queue is empty - no need to log an error
                continue

            except Exception as e:
                log_exception(e)
                continue

    def shutdown(self) -> None:
        """Gracefully shutdown all worker threads."""
        self.is_running = False
        for worker in self.workers:
            worker.join()
            logger.info(f"Profiler {worker.name} shutdown complete")
