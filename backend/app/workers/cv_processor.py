import logging
import os
import shutil
import threading
from datetime import datetime
from queue import Empty, Queue
from typing import Optional

import fitz
from pypdf import PdfReader

from backend.app.config import Configuration
from backend.app.exceptions import (
    CVError,
    CVFormatError,
    CVLengthError,
    log_exception,
)
from backend.app.services.document_intelligence.client import DocumentClient
from backend.app.services.document_intelligence.config import ProcessingConfig
from backend.app.services.document_intelligence.processor import (
    DocumentProcessor,
)
from backend.app.services.users.cv_profile_manager import CVProfileManager
from backend.app.services.users.schemas import CVProfileRunStatus
from backend.app.services.vision.client import VisionAnalysisClient
from backend.app.services.vision.types import CVDescription
from backend.app.workers.profiler import ProfilerWorker

logger = logging.getLogger(__name__)


class CVProcessorWorker:
    """Worker class for processing uploaded CVs using multiple worker threads."""

    _instance: Optional["CVProcessorWorker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CVProcessorWorker, cls).__new__(cls)
            return cls._instance

    def __init__(self, num_workers: int = 2):
        # Only initialize once
        if not hasattr(self, "initialized"):
            self.cv_queue: Queue[tuple[str, str]] = Queue()
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
            self.vision_client = VisionAnalysisClient.from_env()

            # Load any pending CV profiles into the queue
            try:
                cv_profile_manager = CVProfileManager.get_instance()
                pending_cvs = cv_profile_manager.get_pending_cv_profiles()
                for cv in pending_cvs:
                    logger.info(
                        f"Loading pending CV profile run {cv.id} into queue"
                    )
                    self.add_cv_to_queue(cv.id, cv.file_path)
            except Exception as e:
                logger.error(f"Error loading pending CV profile runs: {e}")

            # Create multiple worker threads
            for i in range(num_workers):
                worker = threading.Thread(
                    target=self._process_queue,
                    name=f"CVProcessor-{i}",
                    daemon=True,
                )
                self.workers.append(worker)
                worker.start()
                logger.info(f"Started worker thread {worker.name}")

            self.initialized = True

    def add_cv_to_queue(self, cv_id: str, file_path: str) -> None:
        """Add a CV to the processing queue in a thread-safe manner."""
        with self._lock:
            self.cv_queue.put((cv_id, file_path))
            logger.info(f"Added CV {cv_id} to processing queue")

    def _process_queue(self) -> None:
        """Worker thread that processes CVs from the queue."""
        thread_name = threading.current_thread().name
        logger.info(f"Worker {thread_name} started")

        while self.is_running:
            try:
                # Block for 1 second before checking is_running again
                cv_id, file_path = self.cv_queue.get(timeout=1)

                try:
                    logger.info(f"Worker {thread_name} processing CV {cv_id}")

                    # Each supported file type will be processed differently.
                    # Right now, we only support PDFs.
                    if file_path.lower().endswith(".pdf"):
                        # Extract embedded links from the PDF. This is for links
                        # that might be hyperlinked via text that is not a URL.
                        pypdf_file = open(file_path, "rb")
                        reader = PdfReader(pypdf_file)
                        page_count = len(reader.pages)

                        if page_count > Configuration.CV_MAX_PAGES:
                            raise CVLengthError(
                                f"The file has {page_count} pages, which is more than the maximum allowed ({Configuration.CV_MAX_PAGES})",
                                cv_id,
                            )

                        # Process the document
                        creativity_assessment: Optional[CVDescription] = None
                        paragraphs = self.doc_processor.analyze_paragraphs(
                            file_path, preserve_linebreaks=True
                        )

                        # Extract embedded links from the PDF. This is for links
                        # that might be hyperlinked via text that is not a URL.
                        key = "/Annots"
                        uri = "/URI"
                        ank = "/A"
                        for page in range(page_count):
                            page_object = reader.pages[page]
                            if key in page_object.keys():
                                ann = page_object[key]
                                for a in ann:
                                    u = a.get_object()
                                    if uri in u[ank].keys():
                                        link = u[ank][uri]
                                        # Get the text that was hyperlinked
                                        linked_text = ""
                                        if "/Contents" in u:
                                            linked_text = u["/Contents"]
                                        elif "/T" in u:
                                            linked_text = u["/T"]

                                        # Check if link exists in any paragraph
                                        if not any(
                                            link in para for para in paragraphs
                                        ):
                                            if linked_text:
                                                paragraphs.append(
                                                    f"\n[Found link: '{linked_text}' -> {link}]"
                                                )
                                            else:
                                                paragraphs.append(
                                                    f"\n[Found link: {link}]"
                                                )

                        # Get the directory of the uploaded CV
                        cv_directory = os.path.dirname(file_path)
                        page_filenames = []

                        # Render the PDF pages to images
                        fitz_doc = fitz.open(file_path)
                        cv_page_directory = os.path.join(cv_directory, "pages")
                        os.makedirs(cv_page_directory, exist_ok=True)
                        # Clear any existing files in the pages directory
                        for existing_file in os.listdir(cv_page_directory):
                            file_path = os.path.join(
                                cv_page_directory, existing_file
                            )
                            try:
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                            except Exception as e:
                                logger.error(
                                    f"Error clearing pages directory: {e}"
                                )
                                raise

                        for page in fitz_doc:  # Iterate through the pages
                            page_filename = os.path.join(
                                cv_page_directory, f"page-{page.number}.png"
                            )
                            pix = page.get_pixmap()  # Render page to an image
                            pix.save(page_filename)  # Store image as a PNG
                            page_filenames.append(page_filename)

                        creativity_assessment = (
                            self.vision_client.describe_doc_pages(
                                page_filenames
                            )
                        )
                        if not creativity_assessment:
                            logger.warning(
                                f"Worker {thread_name} failed to generate creativity assessment for CV {cv_id}"
                            )

                        # Clean up the pages directory
                        if os.path.exists(cv_page_directory):
                            try:
                                shutil.rmtree(cv_page_directory)
                                logger.info(
                                    f"Cleaned up pages directory for CV {cv_id}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error cleaning up pages directory for CV {cv_id}: {e}"
                                )
                    else:
                        raise CVFormatError(
                            f"Unsupported file type: {file_path}",
                            cv_id,
                        )

                    cv_profile_manager = CVProfileManager()
                    cv_profile = cv_profile_manager.get_cv_profile(cv_id)
                    cv_profile.updated_at = datetime.now()
                    cv_profile_manager.update_cv_profile(
                        cv_id=cv_id,
                        cv_profile=cv_profile,
                        status=cv_profile.status,
                    )

                    # Send to profiler
                    profiler = ProfilerWorker()
                    profiler.add_to_queue(
                        cv_id, paragraphs, creativity_assessment
                    )

                    logger.info(
                        f"Worker {thread_name} successfully processed CV {cv_id}"
                    )

                except CVError as e:
                    cv_profile_manager = CVProfileManager.get_instance()
                    cv_profile = cv_profile_manager.get_cv_profile(e.cv_id)
                    cv_profile.status = CVProfileRunStatus.FAILED
                    cv_profile_manager.update_cv_profile(
                        cv_id=e.cv_id,
                        cv_profile=cv_profile,
                        status=cv_profile.status,
                        status_comment=str(e),
                    )
                    logger.error(
                        f"Worker {thread_name} encountered an error processing CV {e.cv_id}: {str(e)}"
                    )

                except Exception as e:
                    logger.error(
                        f"Worker {thread_name} encountered an error processing CV {cv_id}: {str(e)}"
                    )

                finally:
                    # Mark task as done even if it failed
                    self.cv_queue.task_done()

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
