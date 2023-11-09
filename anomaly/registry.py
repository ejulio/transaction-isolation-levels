from anomaly.base import ConcurrentTransactionExample

from typing import Dict, List, Tuple, Type


_ANOMALIES: Dict[str, Tuple[Type[ConcurrentTransactionExample], Type[ConcurrentTransactionExample], str]] = dict()


def register(
    anomaly_key: str,
    t1: Type[ConcurrentTransactionExample],
    t2: Type[ConcurrentTransactionExample],
    description: str | None = None
) -> None:
    if anomaly_key in _ANOMALIES:
        raise ValueError(f"Anomaly {anomaly_key} already registered")

    if description:
        description = description.strip()

    _ANOMALIES[anomaly_key] = (t1, t2, description)


def resolve(anomaly: str) -> Tuple[Type[ConcurrentTransactionExample], Type[ConcurrentTransactionExample], str]:
    anomaly = _ANOMALIES.get(anomaly, None)
    if anomaly is None:
        raise ValueError(f"Unknown anomaly: {anomaly}.")

    return anomaly


def get_registered() -> List[str]:
    return list(_ANOMALIES.keys())
