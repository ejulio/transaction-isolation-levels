from anomaly.base import ConcurrentTransactionExample

from typing import List, Tuple, Type


_ANOMALIES = dict()


def register(anomaly: str, t1: Type[ConcurrentTransactionExample], t2: Type[ConcurrentTransactionExample]) -> None:
    if anomaly in _ANOMALIES:
        raise ValueError(f"Anomaly {anomaly} already registered")

    _ANOMALIES[anomaly] = (t1, t2)


def resolve(anomaly: str) -> Tuple[Type[ConcurrentTransactionExample], Type[ConcurrentTransactionExample]]:
    anomaly = _ANOMALIES.get(anomaly, None)
    if anomaly is None:
        raise ValueError(f"Unknown anomaly: {anomaly}.")

    return anomaly


def get_registered() -> List[str]:
    return list(_ANOMALIES.keys())
