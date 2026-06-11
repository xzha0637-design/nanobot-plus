"""边界协议。TaskSpec/WorkerResult 的单一事实源在 contracts.py，这里转出便于按层引用。"""

from ..contracts import TaskSpec, WorkerResult

__all__ = ["TaskSpec", "WorkerResult"]
