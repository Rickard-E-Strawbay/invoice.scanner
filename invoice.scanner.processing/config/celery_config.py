"""
CELERY CONFIGURATION

This file defines all configuration for the Celery task queue.
Sets up:
- Redis connection (broker and result backend)
- Task routing (which tasks go to which workers)
- Worker settings (concurrency, prefetch, etc.)
- Retry strategies
- Result persistence

ARCHITECTURE:
    Redis (Message Broker)
         ↓
    Celery Tasks (in queue)
         ↓
    Workers (preprocessing, ocr, llm, extraction, evaluation)
         ↓
    Redis (Result Backend - store results)

QUEUE ROUTING:
- preprocessing: Light tasks, higher concurrency
- ocr: Compute-intensive, GPU-optimized
- llm: API calls, low concurrency
- extraction: Data structuring
- evaluation: Validation
"""

import os
from kombu import Queue, Exchange
from datetime import timedelta


class CeleryConfig:
    """
    Celery Application Configuration
    
    Environment variables that can be set:
    - REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    - CELERY_BROKER_URL: Explicit broker URL (overrides REDIS_URL)
    - CELERY_RESULT_BACKEND: Explicit result backend (overrides REDIS_URL)
    """
    
    # ===== BROKER AND RESULT BACKEND =====
    # Redis is used for both message queue (broker) and result storage (result backend)
    
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Message Broker - where tasks are queued
    broker_url = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    
    # Result Backend - where task results are stored
    result_backend = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    # ===== RESULT SETTINGS =====
    result_expires = 3600  # Results stored for 1 hour
    result_persistent = True  # Store results between restarts
    
    # ===== TASK SETTINGS =====
    task_track_started = True  # Track when tasks start
    task_send_sent_event = True  # Skicka event när task skickas
    task_acks_late = True  # Bekräfta task först när den är klar
    task_reject_on_worker_lost = True  # Skicka task tillbaka om worker dör
    
    # Timeout för tasks
    task_soft_time_limit = 300  # 5 minuter - soft timeout (SoftTimeLimitExceeded exception)
    task_time_limit = 600  # 10 minuter - hard timeout (task kills)
    
    # ===== WORKER INSTÄLLNINGAR =====
    # Prefetch multiplier - hur många tasks en worker ska hämta i förväg
    # Satt till 1 för att undvika att en långsam task blockerar andra
    worker_prefetch_multiplier = 1
    
    # Max retries för failed tasks
    task_max_retries = 3
    
    # ===== TASK ROUTING =====
    # Vilka tasks går till vilka queues/workers
    # Detta är KRITISKT för optimal prestanda!
    
    task_routes = {
        # Document orchestration - main entry point for processing
        'tasks.document_tasks.*': {'queue': 'preprocessing'},
        
        # Preprocessing tasks - lätta, parallella
        'tasks.preprocessing_tasks.*': {'queue': 'preprocessing'},
        
        # OCR tasks - beräkningstung, GPU
        'tasks.ocr_tasks.*': {'queue': 'ocr'},
        
        # LLM tasks - API-anrop, låga i antal
        'tasks.llm_tasks.*': {'queue': 'llm'},
        
        # Extraction tasks - data strukturering
        'tasks.extraction_tasks.*': {'queue': 'extraction'},
        
        # Evaluation tasks - validering
        'tasks.evaluation_tasks.*': {'queue': 'evaluation'},
    }
    
    # ===== QUEUE DEFINITIONS =====
    # Definiera alla queues och deras properties
    
    # DEFAULT QUEUE - vart tasks hamnar om de inte har explicit routing
    task_default_queue = 'preprocessing'
    
    default_exchange = Exchange('celery', type='direct', durable=True)
    
    task_queues = (
        # PREPROCESSING QUEUE
        # - Lätta image processing tasks
        # - Högt parallellism (4 workers, 4 concurrency)
        # - Snabbt genomförande
        Queue(
            'preprocessing',
            exchange=default_exchange,
            routing_key='preprocessing',
            durable=True,
            queue_arguments={
                'x-max-priority': 10  # Prioritera tasks
            }
        ),
        
        # OCR QUEUE
        # - Beräkningstung (Tesseract/PaddleOCR)
        # - GPU-accelererad om tillgängligt
        # - Lågt parallellism (2 workers, 2 concurrency max)
        Queue(
            'ocr',
            exchange=default_exchange,
            routing_key='ocr',
            durable=True,
            queue_arguments={
                'x-max-priority': 8
            }
        ),
        
        # LLM QUEUE
        # - API-anrop (OpenAI, Gemini, Anthropic)
        # - Höga latenser (timeout ofta)
        # - Låg concurrency (1 worker)
        # - Robust retry strategy
        Queue(
            'llm',
            exchange=default_exchange,
            routing_key='llm',
            durable=True,
            queue_arguments={
                'x-max-priority': 6
            }
        ),
        
        # EXTRACTION QUEUE
        # - Data strukturering och validering
        # - Låg CPU
        # - Medel parallellism (3 concurrency)
        Queue(
            'extraction',
            exchange=default_exchange,
            routing_key='extraction',
            durable=True,
            queue_arguments={
                'x-max-priority': 7
            }
        ),
        
        # EVALUATION QUEUE
        # - Slutlig validering
        # - Låg CPU
        # - Kan batcha mehrere document evaluations
        Queue(
            'evaluation',
            exchange=default_exchange,
            routing_key='evaluation',
            durable=True,
            queue_arguments={
                'x-max-priority': 5
            }
        ),
    )
    
    # ===== RETRY STRATEGIES =====
    # Exponential backoff för olika typer av failures
    
    task_autoretry_for = (Exception,)
    
    # Task retry inställningar per typ
    RETRY_STRATEGIES = {
        'preprocessing': {
            'max_retries': 2,
            'countdown': 60,  # 1 minut
        },
        'ocr': {
            'max_retries': 3,
            'countdown': 120,  # 2 minuter
        },
        'llm': {
            'max_retries': 3,
            'countdown': 300,  # 5 minuter - längre för API-calls
        },
        'extraction': {
            'max_retries': 2,
            'countdown': 60,
        },
        'evaluation': {
            'max_retries': 2,
            'countdown': 60,
        },
    }
    
    # ===== TIMEZONE =====
    timezone = 'UTC'
    enable_utc = True
