"""Pluggable methodology interface for carbon-credit quantification engines.

All methodology-specific calc engines (ACM0022, AMS-II.G, VM0051, VM0044, …)
implement `MethodologyEngine`.  Callers can therefore compute baseline, project,
leakage, and net emissions through a uniform contract without knowing the
underlying formulas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ValidationResult:
    """Outcome of validating a raw input dict for a methodology engine."""

    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ComputationResult:
    """A single quantification result with full provenance."""

    value: float
    unit: str
    formula: str
    provenance: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


@runtime_checkable
class MethodologyEngine(Protocol):
    """Protocol implemented by every quantification methodology engine.

    Engines are stateless with respect to a particular project: each `compute_*`
    and `validate_inputs` call receives the inputs it needs as a dict.  This
    makes the protocol easy to wire into orchestrators, FastAPI endpoints, and
    tests.
    """

    def methodology_id(self) -> str:
        """Return the canonical methodology ID (e.g. ``"ACM0022"``)."""
        ...

    def validate_inputs(self, inputs: dict[str, Any]) -> ValidationResult:
        """Validate a raw input dict without performing any calculation."""
        ...

    def compute_baseline(self, inputs: dict[str, Any]) -> ComputationResult:
        """Baseline emissions for the given inputs."""
        ...

    def compute_project(self, inputs: dict[str, Any]) -> ComputationResult:
        """Project emissions for the given inputs."""
        ...

    def compute_leakage(self, inputs: dict[str, Any]) -> ComputationResult:
        """Leakage emissions for the given inputs."""
        ...

    def compute_net(self, inputs: dict[str, Any]) -> ComputationResult:
        """Net emission reductions (or removals) for the given inputs."""
        ...

    def required_monitoring_params(self, inputs: dict[str, Any]) -> list[dict]:
        """Return the monitoring parameters required by the methodology.

        Each entry is a dict with keys such as ``id``, ``name``, ``unit``,
        ``frequency``, ``source``, and ``section_ref``.
        """
        ...
