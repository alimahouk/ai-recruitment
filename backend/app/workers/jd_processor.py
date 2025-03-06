import logging
import threading
from datetime import datetime
from queue import Empty, Queue
from typing import Optional

from pypdf import PdfReader

from backend.app.config import Configuration
from backend.app.exceptions import (
    JDFormatError,
    JDLengthError,
    RoleListingError,
    log_exception,
)
from backend.app.services.document_intelligence.client import DocumentClient
from backend.app.services.document_intelligence.config import ProcessingConfig
from backend.app.services.document_intelligence.processor import (
    DocumentProcessor,
)
from backend.app.services.llm.processor import LLMProcessor
from backend.app.services.roles.role_listing_manager import RoleListingManager
from backend.app.services.roles.role_profile_manager import RoleProfileManager
from backend.app.services.roles.schemas import RoleListingRunStatus

logger = logging.getLogger(__name__)


class JDProcessorWorker:
    """Worker class for processing uploaded job descriptions using multiple worker threads."""

    _instance: Optional["JDProcessorWorker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(JDProcessorWorker, cls).__new__(cls)
            return cls._instance

    def __init__(self, num_workers: int = 2):
        # Only initialize once
        if not hasattr(self, "initialized"):
            self.jd_queue: Queue[tuple[str, str]] = Queue()
            self.is_running = True
            self.workers: list[threading.Thread] = []
            self.doc_processor = DocumentProcessor(
                client=DocumentClient.from_env(),
                config=ProcessingConfig(
                    min_confidence=0.8,
                    include_tables=True,
                    include_figures=True,
                    clean_text=True,
                ),
            )
            self.llm_processor = LLMProcessor.from_env()

            # Load any pending role listing jobs into the queue
            try:
                jd_profile_manager = RoleProfileManager.get_instance()
                pending_jds = jd_profile_manager.get_pending_role_profiles()
                for jd in pending_jds:
                    logger.info(
                        f"Loading pending JD profile run {jd.id} into queue"
                    )
                    self.add_jd_to_queue(jd.id, jd.file_path)
            except Exception as e:
                logger.error(f"Error loading pending JD profile runs: {e}")

            # Create multiple worker threads
            for i in range(num_workers):
                worker = threading.Thread(
                    target=self._process_queue,
                    name=f"JDProcessor-{i}",
                    daemon=True,
                )
                self.workers.append(worker)
                worker.start()
                logger.info(f"Started worker thread {worker.name}")

            self.initialized = True

    def add_jd_to_queue(self, jd_id: str, file_path: str) -> None:
        """Add a JD to the processing queue in a thread-safe manner."""
        with self._lock:
            self.jd_queue.put((jd_id, file_path))
            logger.info(f"Added JD {jd_id} to processing queue")

    def _process_queue(self) -> None:
        """Worker thread that processes JDs from the queue."""
        thread_name = threading.current_thread().name
        logger.info(f"Worker {thread_name} started")

        while self.is_running:
            try:
                # Block for 1 second before checking is_running again
                jd_id, file_path = self.jd_queue.get(timeout=1)

                try:
                    logger.info(f"Worker {thread_name} processing JD {jd_id}")
                    role_profile_manager = RoleProfileManager.get_instance()
                    role_profile_run = role_profile_manager.get_role_profile(
                        jd_id
                    )
                    if not role_profile_run:
                        raise RoleListingError(
                            f"Role profile run {jd_id} not found", jd_id
                        )

                    role_profile_run.updated_at = datetime.now()
                    role_profile_run = role_profile_manager.update_role_profile(
                        role_id=jd_id,
                        role_profile=role_profile_run,
                        creator_id=role_profile_run.creator_id,
                        status=role_profile_run.status,
                    )

                    if file_path.lower().endswith(".pdf"):
                        # Check page count
                        pypdf_file = open(file_path, "rb")
                        reader = PdfReader(pypdf_file)
                        page_count = len(reader.pages)

                        if page_count > Configuration.JD_MAX_PAGES:
                            raise JDLengthError(
                                f"The file has {page_count} pages, which is more than the maximum allowed ({Configuration.JD_MAX_PAGES})",
                                jd_id,
                            )

                        # Process the document
                        paragraphs = self.doc_processor.analyze_paragraphs(
                            file_path, preserve_linebreaks=True
                        )

                    else:
                        raise JDFormatError(
                            f"Unsupported file type: {file_path}",
                            jd_id,
                        )

                    # Process JD content using LLM
                    jd_analysis = self.llm_processor.analyze_jd(
                        paragraphs=paragraphs
                    )

                    role_profile_run.updated_at = datetime.now()
                    role_profile_run.status = RoleListingRunStatus.COMPLETED
                    role_profile_run = role_profile_manager.update_role_profile(
                        role_id=jd_id,
                        role_profile=jd_analysis,
                        creator_id=role_profile_run.creator_id,
                        status=role_profile_run.status,
                    )

                    role_listing_manager = RoleListingManager.get_instance()
                    role_listing_manager.add_role_from_profile(role_profile_run)
                    role_profile_manager.delete_role_profile(
                        role_profile_run.id
                    )  # No longer needed

                    logger.info(
                        f"Worker {thread_name} successfully processed JD {jd_id}"
                    )

                except RoleListingError as e:
                    role_profile_manager = RoleProfileManager.get_instance()
                    role_profile_run = role_profile_manager.get_role_profile(
                        e.jd_id
                    )
                    if role_profile_run:
                        role_profile_run.status = RoleListingRunStatus.FAILED
                        role_profile_manager.update_role_profile(
                            role_id=e.jd_id,
                            role_profile=role_profile_run,
                            creator_id=role_profile_run.creator_id,
                            status=role_profile_run.status,
                            status_comment=str(e),
                        )
                    logger.error(
                        f"Worker {thread_name} encountered an error processing JD {e.jd_id}: {str(e)}"
                    )

                except Exception as e:
                    logger.error(
                        f"Worker {thread_name} encountered an error processing JD {jd_id}: {str(e)}"
                    )

                finally:
                    # Mark task as done even if it failed
                    self.jd_queue.task_done()

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
            logger.info(f"Worker {worker.name} shutdown complete")
