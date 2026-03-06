"""
Formula Engine — Configurator §6 Step 2.
Evaluates sizing formula expressions (e.g. max(min_cpu, ceil(rps / rps_per_cpu)))
against a variable context. Uses simpleeval for safe evaluation.
"""
import logging
import math
from typing import Any, Dict

try:
    from simpleeval import SimpleEval
except ImportError:
    SimpleEval = None  # type: ignore

logger = logging.getLogger(__name__)


def _make_evaluator() -> "SimpleEval":
    if SimpleEval is None:
        raise ImportError("simpleeval is required for formula evaluation. pip install simpleeval")
    ev = SimpleEval()
    ev.functions["ceil"] = math.ceil
    ev.functions["floor"] = math.floor
    ev.functions["max"] = max
    ev.functions["min"] = min
    ev.functions["round"] = round
    return ev


def evaluate_sizing_formulas(
    formulas: Dict[str, str],
    variables: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate each formula expression with the given variable context.
    Returns a dict of resource_type -> numeric value (int or float).
    """
    if not formulas:
        return {}
    try:
        ev = _make_evaluator()
    except ImportError as e:
        logger.warning("Formula engine unavailable: %s. Sizing will use defaults only.", e)
        return {}

    result: Dict[str, Any] = {}
    for resource_type, expression in formulas.items():
        if not expression or not expression.strip():
            continue
        try:
            ev.names = dict(variables)
            value = ev.eval(expression.strip())
            if value is not None and isinstance(value, (int, float)):
                result[resource_type] = int(value) if isinstance(value, float) and value == int(value) else value
            else:
                logger.debug("Formula %s for %s returned non-numeric: %s", expression, resource_type, value)
        except Exception as e:
            logger.warning(
                "Formula evaluation failed for %s = %r: %s. Variables: %s",
                resource_type,
                expression,
                e,
                list(variables.keys()),
            )
    return result


def evaluate_expression(expression: str, variables: Dict[str, Any]) -> Any:
    """Evaluate a single formula expression with the given variables. For validate-formula API."""
    if not expression or not expression.strip():
        raise ValueError("Empty expression")
    ev = _make_evaluator()
    ev.names = dict(variables)
    return ev.eval(expression.strip())
