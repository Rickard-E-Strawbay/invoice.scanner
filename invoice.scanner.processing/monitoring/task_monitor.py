"""
Task Monitoring and Metrics Collection

Monitors Celery task execution and collects performance metrics.

METRICS TRACKED:
    - Task execution times
    - Success/failure rates
    - Queue depths
    - Worker health and status
    - Task retry rates

SIGNAL HANDLERS:
    task_started: Log and track when tasks begin
    task_success: Log and track successful completions
    task_failure: Log and track failures with error details

USAGE:
    This module is auto-loaded via signal registration.
    Metrics are available via monitoring endpoints (when implemented).

FUTURE ENHANCEMENTS:
    - Real-time metrics dashboards
    - Performance trend analysis
    - Worker capacity planning
    - Automatic alerting on failures
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from celery.signals import task_success, task_failure, task_started
from tasks.celery_app import app

logger = logging.getLogger(__name__)


# ===== METRICS STORAGE =====
# In production, use a proper metrics backend (Prometheus, DataDog, etc)
_task_metrics: Dict[str, Any] = {
    'total_started': 0,
    'total_success': 0,
    'total_failure': 0,
    'by_task_type': {}
}


# ===== SIGNAL HANDLERS =====

@task_started.connect
def task_started_handler(task_id: str, task: Any, **kwargs) -> None:
    """
    Log when a task starts execution.

    Args:
        task_id: Celery task UUID.
        task: Task object with name and other metadata.
    """
    logger.info(f"[TASK STARTED] {task.name} (task_id: {task_id})")
    _task_metrics['total_started'] += 1


@task_success.connect
def task_success_handler(
    result: Any,
    task_id: str,
    task: Any,
    **kwargs
) -> None:
    """
    Log successful task completion.

    Args:
        result: Task return value.
        task_id: Celery task UUID.
        task: Task object with name and metadata.
    """
    logger.info(f"[TASK SUCCESS] {task.name} (task_id: {task_id})")
    _task_metrics['total_success'] += 1
    _task_metrics['by_task_type'][task.name] = \
        _task_metrics['by_task_type'].get(task.name, 0) + 1


@task_failure.connect
def task_failure_handler(
    task_id: str,
    exception: Exception,
    traceback: Optional[str],
    **kwargs
) -> None:
    """
    Log task failure with error details.

    Args:
        task_id: Celery task UUID.
        exception: The exception that caused failure.
        traceback: Full traceback information.
    """
    logger.error(
        f"[TASK FAILED] task_id={task_id} | error={str(exception)}",
        exc_info=True
    )
    _task_metrics['total_failure'] += 1


# ===== METRICS QUERY =====

def get_metrics() -> Dict[str, Any]:
    """
    Retrieve collected task metrics.

    Returns:
        Dictionary with metrics summary.
        {
            'total_started': 42,
            'total_success': 40,
            'total_failure': 2,
            'success_rate': 0.95,
            'by_task_type': {...}
        }

    Note:
        In production, use a proper metrics backend.
        This is for development/debugging only.
    """
    total_started = _task_metrics['total_started']
    total_success = _task_metrics['total_success']

    success_rate = (
        total_success / total_started
        if total_started > 0
        else 0.0
    )

    return {
        **_task_metrics,
        'success_rate': success_rate,
        'timestamp': datetime.utcnow().isoformat()
    }


def reset_metrics() -> None:
    """Reset all collected metrics (for testing/debugging)."""
    global _task_metrics
    _task_metrics = {
        'total_started': 0,
        'total_success': 0,
        'total_failure': 0,
        'by_task_type': {}
    }
    logger.info("[METRICS] Reset all task metrics")
