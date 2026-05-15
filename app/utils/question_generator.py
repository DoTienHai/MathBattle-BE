"""Pure algorithm for generating math questions at a given difficulty level (SF09)."""

import random
import logging
from dataclasses import dataclass
from typing import NamedTuple

logger = logging.getLogger(__name__)

OP_ADD = "+"
OP_SUB = "-"
OP_MUL = "×"  # U+00D7
OP_DIV = "÷"  # U+00F7

OP_SUB_LEVEL_START = 5
OP_MUL_OR_DIV_LEVEL_START = 15
OP_MUL_AND_DIV_LEVEL_START = 30


WEIGHTS = {
    OP_ADD: 5,
    OP_SUB: 3,
    OP_MUL: 2,
    OP_DIV: 1,
}
DIFFICULTY_COEFFICIENT = 15

MAX_RANGE_LEVELS = 2*[10] + 3*[20] + 5*[30] + 7*[50] + 11*[100] + 13*[200] + 17*[500] + 19*[1000]

class GenerationError(Exception):
    """Custom exception for errors during question generation."""

@dataclass(frozen=True)
class QuestionConfig:
    """Question generation configuration for a given difficulty level.

    ops is the *exact* operator sequence for the expression, left to right.
    Example: [OP_ADD, OP_SUB] → a + b - c = ?

    Attributes:
        min: Lower bound for operand values (inclusive).
        max: Upper bound for operand values (inclusive).
        ops: Ordered list of operators; len(ops) + 1 operands are generated.
    """
    min: int
    max: int
    ops: list[str]


# ── Public API ────────────────────────────────────────────────────────────────


def get_question_config(level: int) -> QuestionConfig:
    """Return a QuestionConfig for the given difficulty level.

    Number of operators grows by 1 every DIFFICULTY_COEFFICIENT levels.
    Available operators expand at level thresholds (OP_SUB_LEVEL_START,
    OP_MUL_DIV_LEVEL_START) and are sampled with WEIGHTS.
    Selecting × or ÷ reduces effective_level to lower the operand range,
    compensating for the larger values produced by multiplication.

    Args:
        level: Ramp level from SF06 (≥ 1).

    Returns:
        QuestionConfig with a randomly chosen operator list and a matching
        operand range scaled to the effective difficulty.
    """
    number_of_operator = 1+level// DIFFICULTY_COEFFICIENT
    
    allowable_operators = [OP_ADD]
    if level >= OP_SUB_LEVEL_START:
        allowable_operators.append(OP_SUB)
    if level >= OP_MUL_OR_DIV_LEVEL_START:
        allowable_operators.append(random.choice([OP_MUL, OP_DIV]))
    if level >= OP_MUL_AND_DIV_LEVEL_START:
        allowable_operators.append(OP_MUL)
        allowable_operators.append(OP_DIV)

    effective_level = level
    ops = []
    for _ in range(number_of_operator):
        op = random.choices(
            population=allowable_operators,
            weights=[WEIGHTS[o] for o in allowable_operators],
            k=1
        )[0]
        if op in [OP_DIV, OP_MUL]:
            effective_level = 1 + effective_level//(DIFFICULTY_COEFFICIENT//2)
        ops.append(op)

    effective_level = 1 + (effective_level+level)//(DIFFICULTY_COEFFICIENT//2)
    range_min = 1
    range_max = MAX_RANGE_LEVELS[min(effective_level - 1, len(MAX_RANGE_LEVELS) - 1)]
    
    return QuestionConfig(
        min=range_min,
        max=range_max,
        ops=ops,
    )


def generate_math_question(level: int) -> dict[str, int | str]:
    """Generate a random math question at the given difficulty level.

    Operator sequence is determined by get_question_config; only operand
    values are randomized.

    Args:
        level: Ramp difficulty level (≥ 1) from SF06 formula.

    Returns:
        {"content": "12 + 5 - 3 = ?", "correct_answer": 14}
    """
    config = get_question_config(level)
    nums, result = generate_expression(config)
    content = build_display_string(nums, config.ops)
    return {"content": content, "correct_answer": result}


# ── Helpers ───────────────────────────────────────────────────────────────────


def is_prime(n: int) -> bool:
    """Return True if n is a prime number (trial division).

    Args:
        n: Integer to test.

    Returns:
        True if n is prime.
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def _get_divisors(n: int, max_val: int) -> list[int]:
    """Return positive divisors of n that are ≤ max_val.

    If n is prime and n > max_val, also include n itself so that
    acc ÷ acc = 1 is always available as a fallback.

    Args:
        n: The number whose divisors to find (must be ≥ 1).
        max_val: Upper bound for divisors.

    Returns:
        Non-empty list of positive integer divisors.
    """
    limit = min(n, max_val)
    divs = [d for d in range(1, limit + 1) if n % d == 0]
    if is_prime(n) and n > max_val:
        divs.append(n)
    return divs


def generate_expression(
    config: QuestionConfig
) -> tuple[list[int], int]:
    """Generate operands for a predefined operator sequence.

    Uses a single unified operator-precedence algorithm: ops are first grouped into
    additive terms, where each term is a chain of × / ÷.  Operands within
    a term are generated so that division always produces a whole number
    (divisor is drawn from _get_divisors).  The final result is the signed
    sum of all term values.

    Args:
        config: Level configuration with operand range and operator list.

    Returns:
        (nums, result) — nums has len(ops)+1 elements in expression order.
    """
    mn, mx = config.min, config.max

    # Split ops into additive terms.
    # term_signs[i]:    +1 / -1 for the i-th additive term
    # term_mul_ops[i]:  internal × / ÷ operators within that term
    term_signs: list[int] = [1]
    term_mul_ops: list[list[str]] = [[]]
    for op in config.ops:
        if op in [OP_ADD, OP_SUB]:
            if op == OP_ADD:
                term_signs.append(1)
            else:
                term_signs.append(-1)
            term_mul_ops.append([])
        else:
            term_mul_ops[-1].append(op)
    
    nums = []
    term_values: list[int] = []
    for mul_ops in term_mul_ops:
        n0 = random.randint(mn, mx)
        nums.append(n0)
        acc = n0
        for op in mul_ops:
            if op == OP_MUL:
                b = random.randint(mn, mx)
                acc *= b
            else:  # OP_DIV
                divs = _get_divisors(acc, mx)
                b = random.choice(divs)
                acc //= b
            nums.append(b)
        term_values.append(acc)
    result = sum(s * v for s, v in zip(term_signs, term_values))

    return nums, result

def build_display_string(nums: list[int], ops: list[str]) -> str:
    """Format operands and operators into a display string ending with '= ?'.

    Operators × and ÷ are already Unicode; + and - are passed through as-is.

    Args:
        nums: Operand list.
        ops: Operator list.

    Returns:
        E.g. "12 + 5 × 3 - 4 = ?"
    """
    parts = [str(nums[0])]
    for op, n in zip(ops, nums[1:]):
        parts += [op, str(n)]
    parts.append("= ?")
    return " ".join(parts)


if __name__ == "__main__":
    # Quick test: generate 5 questions at each of the first 30 levels.
    for lvl in range(1, 101, 10):
        print(f"Level {lvl}:")
        for _ in range(5):
            q = generate_math_question(lvl)
            print(f"  {q['content']} (answer: {q['correct_answer']})")