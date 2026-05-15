"""Unit tests for app/utils/question_generator.py (SF09)."""

import pytest

from app.utils.question_generator import (
    DIFFICULTY_COEFFICIENT,
    OP_ADD,
    OP_DIV,
    OP_MUL,
    OP_MUL_AND_DIV_LEVEL_START,
    OP_MUL_OR_DIV_LEVEL_START,
    OP_SUB,
    OP_SUB_LEVEL_START,
    GenerationError,
    QuestionConfig,
    _get_divisors,
    build_display_string,
    generate_expression,
    generate_math_question,
    get_question_config,
    is_prime,
)

_SAMPLE_N = 300
_ADDITIVE = {OP_ADD, OP_SUB}
_MULTIPLICATIVE = {OP_MUL, OP_DIV}


def _eval_pemdas(nums: list[int], ops: list[str]) -> int:
    """Evaluate a numeric expression using PEMDAS (× ÷ before + −)."""
    vals, ops_ = list(nums), list(ops)
    i = 0
    while i < len(ops_):
        if ops_[i] in _MULTIPLICATIVE:
            v = vals[i] * vals[i + 1] if ops_[i] == OP_MUL else vals[i] // vals[i + 1]
            vals = vals[:i] + [v] + vals[i + 2 :]
            ops_ = ops_[:i] + ops_[i + 1 :]
        else:
            i += 1
    result = vals[0]
    for op, v in zip(ops_, vals[1:]):
        result += v if op == OP_ADD else -v
    return result


# ── is_prime ──────────────────────────────────────────────────────────────────


def test_is_prime_identifies_small_primes():
    assert all(is_prime(n) for n in [2, 3, 5, 7, 11, 13, 17, 19])


def test_is_prime_rejects_composites_and_edge_cases():
    assert not any(is_prime(n) for n in [0, 1, 4, 6, 8, 9, 10, 15, 25, 100])


def test_is_prime_rejects_negative():
    assert is_prime(-7) is False


# ── _get_divisors ─────────────────────────────────────────────────────────────


def test_get_divisors_returns_correct_set():
    assert set(_get_divisors(12, 20)) == {1, 2, 3, 4, 6, 12}


def test_get_divisors_respects_max_val():
    divs = _get_divisors(12, 4)
    assert set(divs) == {1, 2, 3, 4}
    assert 6 not in divs and 12 not in divs


def test_get_divisors_prime_within_range():
    divs = _get_divisors(7, 10)
    assert 1 in divs and 7 in divs


def test_get_divisors_prime_fallback_when_prime_exceeds_max():
    # 7 is prime and > max_val=5 — must append 7 itself so acc÷acc=1 is available
    divs = _get_divisors(7, 5)
    assert 7 in divs
    assert 1 in divs


def test_get_divisors_is_never_empty():
    # 1 always divides any n ≥ 1, so the list can never be empty
    for n in range(1, 50):
        for mx in range(1, 20):
            assert len(_get_divisors(n, mx)) > 0, f"Empty for n={n}, max_val={mx}"


def test_get_divisors_all_entries_divide_n():
    for n in [6, 12, 30, 100]:
        for d in _get_divisors(n, 100):
            assert n % d == 0, f"{d} does not divide {n}"


# ── QuestionConfig ────────────────────────────────────────────────────────────


def test_question_config_is_frozen():
    cfg = QuestionConfig(min=1, max=10, ops=[OP_ADD])
    with pytest.raises((AttributeError, TypeError)):
        cfg.min = 5  # type: ignore


def test_question_config_stores_values():
    cfg = QuestionConfig(min=1, max=20, ops=[OP_ADD, OP_SUB])
    assert cfg.min == 1
    assert cfg.max == 20
    assert cfg.ops == [OP_ADD, OP_SUB]


# ── get_question_config ───────────────────────────────────────────────────────


def test_config_level_1_always_single_addition():
    # Only + is in allowable at level 1, num_ops = 1 → always [OP_ADD]
    for _ in range(50):
        cfg = get_question_config(1)
        assert cfg.ops == [OP_ADD]
        assert cfg.min == 1
        assert cfg.max >= 1


def test_config_min_is_always_one():
    for level in [1, 5, 15, 30, 50, 94, 200]:
        assert get_question_config(level).min == 1


def test_config_max_is_positive():
    for level in [1, 5, 15, 30, 50, 94, 200]:
        assert get_question_config(level).max >= 1


def test_config_num_ops_follows_formula():
    # num_ops = 1 + level // DIFFICULTY_COEFFICIENT
    for level in [1, 14, 15, 29, 30, 44, 45, 59]:
        expected = 1 + level // DIFFICULTY_COEFFICIENT
        for _ in range(20):
            cfg = get_question_config(level)
            assert len(cfg.ops) == expected, (
                f"Level {level}: expected {expected} ops, got {len(cfg.ops)}"
            )


def test_config_below_sub_threshold_never_has_subtraction():
    for level in range(1, OP_SUB_LEVEL_START):
        for _ in range(30):
            cfg = get_question_config(level)
            assert OP_SUB not in cfg.ops, f"Level {level}: unexpected − in {cfg.ops}"
            assert OP_MUL not in cfg.ops
            assert OP_DIV not in cfg.ops


def test_config_at_sub_threshold_can_produce_subtraction():
    seen = False
    for _ in range(300):
        if OP_SUB in get_question_config(OP_SUB_LEVEL_START).ops:
            seen = True
            break
    assert seen, f"Level {OP_SUB_LEVEL_START} never produced OP_SUB"


def test_config_below_mul_threshold_never_has_multiply_or_divide():
    for level in range(1, OP_MUL_OR_DIV_LEVEL_START):
        for _ in range(30):
            cfg = get_question_config(level)
            assert OP_MUL not in cfg.ops, f"Level {level}: unexpected × in {cfg.ops}"
            assert OP_DIV not in cfg.ops, f"Level {level}: unexpected ÷ in {cfg.ops}"


def test_config_at_mul_threshold_can_produce_mul_or_div():
    seen = False
    for _ in range(300):
        cfg = get_question_config(OP_MUL_OR_DIV_LEVEL_START)
        if OP_MUL in cfg.ops or OP_DIV in cfg.ops:
            seen = True
            break
    assert seen, f"Level {OP_MUL_OR_DIV_LEVEL_START} never produced × or ÷"


def test_config_at_both_mul_div_threshold_can_produce_each():
    seen_mul = seen_div = False
    for _ in range(500):
        cfg = get_question_config(OP_MUL_AND_DIV_LEVEL_START)
        if OP_MUL in cfg.ops:
            seen_mul = True
        if OP_DIV in cfg.ops:
            seen_div = True
        if seen_mul and seen_div:
            break
    assert seen_mul, f"Level {OP_MUL_AND_DIV_LEVEL_START} never produced ×"
    assert seen_div, f"Level {OP_MUL_AND_DIV_LEVEL_START} never produced ÷"


def test_config_ops_contains_only_valid_operators():
    valid = {OP_ADD, OP_SUB, OP_MUL, OP_DIV}
    for level in range(1, 95):
        cfg = get_question_config(level)
        for op in cfg.ops:
            assert op in valid, f"Level {level}: unknown op '{op}'"


def test_config_very_high_level_does_not_crash():
    cfg = get_question_config(999)
    assert cfg.min == 1
    assert cfg.max > 0
    assert len(cfg.ops) >= 1


# ── build_display_string ──────────────────────────────────────────────────────


def test_build_display_ends_with_equals_question():
    assert build_display_string([1, 2], [OP_ADD]).endswith("= ?")


def test_build_display_single_addition():
    assert build_display_string([3, 4], [OP_ADD]) == "3 + 4 = ?"


def test_build_display_single_subtraction():
    assert build_display_string([10, 3], [OP_SUB]) == "10 - 3 = ?"


def test_build_display_uses_unicode_multiplication_symbol():
    s = build_display_string([3, 4], [OP_MUL])
    assert "×" in s
    assert "*" not in s


def test_build_display_uses_unicode_division_symbol():
    s = build_display_string([12, 4], [OP_DIV])
    assert "÷" in s
    assert "/" not in s


def test_build_display_multi_operator_format():
    s = build_display_string([12, 5, 3, 4], [OP_ADD, OP_MUL, OP_SUB])
    assert s == "12 + 5 × 3 - 4 = ?"


def test_build_display_token_count_matches_operands_and_ops():
    for num_ops in range(1, 5):
        nums = list(range(1, num_ops + 2))
        ops = [OP_ADD] * num_ops
        tokens = build_display_string(nums, ops).replace(" = ?", "").split()
        # n operands + (n-1) operators = 2n-1 tokens
        assert len(tokens) == 2 * (num_ops + 1) - 1


# ── generate_expression ───────────────────────────────────────────────────────


def test_expression_single_addition():
    cfg = QuestionConfig(min=1, max=20, ops=[OP_ADD])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        assert len(nums) == 2
        assert result == nums[0] + nums[1]


def test_expression_single_subtraction():
    cfg = QuestionConfig(min=1, max=20, ops=[OP_SUB])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        assert len(nums) == 2
        assert result == nums[0] - nums[1]


def test_expression_single_multiplication():
    cfg = QuestionConfig(min=1, max=20, ops=[OP_MUL])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        assert len(nums) == 2
        assert result == nums[0] * nums[1]


def test_expression_single_division_is_exact():
    cfg = QuestionConfig(min=1, max=50, ops=[OP_DIV])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        assert len(nums) == 2
        assert nums[0] % nums[1] == 0, f"{nums[0]} ÷ {nums[1]} not exact"
        assert result == nums[0] // nums[1]
        assert isinstance(result, int)


def test_expression_operand_count_equals_ops_plus_one():
    for num_ops in range(1, 5):
        cfg = QuestionConfig(min=1, max=20, ops=[OP_ADD] * num_ops)
        for _ in range(10):
            nums, _ = generate_expression(cfg)
            assert len(nums) == num_ops + 1


def test_expression_additive_operands_in_range():
    cfg = QuestionConfig(min=1, max=30, ops=[OP_ADD, OP_SUB, OP_ADD])
    for _ in range(_SAMPLE_N):
        nums, _ = generate_expression(cfg)
        assert all(1 <= n <= 30 for n in nums), f"Operand out of range: {nums}"


def test_expression_multiplicative_operands_in_range():
    cfg = QuestionConfig(min=1, max=15, ops=[OP_MUL, OP_MUL])
    for _ in range(_SAMPLE_N):
        nums, _ = generate_expression(cfg)
        assert all(1 <= n <= 15 for n in nums), f"Operand out of range: {nums}"


def test_expression_result_matches_pemdas_for_mixed_ops():
    """For any operator sequence, result must equal PEMDAS evaluation."""
    cases = [
        [OP_ADD, OP_MUL],
        [OP_MUL, OP_ADD],
        [OP_ADD, OP_SUB, OP_MUL],
        [OP_MUL, OP_SUB],
        [OP_ADD, OP_MUL, OP_SUB, OP_DIV],
    ]
    for ops in cases:
        cfg = QuestionConfig(min=1, max=20, ops=ops)
        for _ in range(50):
            nums, result = generate_expression(cfg)
            expected = _eval_pemdas(nums, ops)
            assert result == expected, f"ops={ops}, nums={nums}: got {result}, expected {expected}"


def test_expression_pemdas_precedence_mul_before_add():
    # a + b × c must equal a + (b*c), not (a+b)*c
    cfg = QuestionConfig(min=1, max=10, ops=[OP_ADD, OP_MUL])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        a, b, c = nums
        assert result == a + (b * c), f"{a} + {b} × {c}: got {result}"


def test_expression_pemdas_precedence_mul_before_sub():
    # a - b × c must equal a - (b*c)
    cfg = QuestionConfig(min=1, max=10, ops=[OP_SUB, OP_MUL])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        a, b, c = nums
        assert result == a - (b * c), f"{a} - {b} × {c}: got {result}"


def test_expression_division_in_chain_always_exact():
    cfg = QuestionConfig(min=1, max=20, ops=[OP_MUL, OP_DIV])
    for _ in range(_SAMPLE_N):
        nums, result = generate_expression(cfg)
        assert isinstance(result, int)
        assert result == _eval_pemdas(nums, [OP_MUL, OP_DIV])


def test_expression_subtraction_can_yield_negative():
    # No constraint: a - b - c - d can go negative
    cfg = QuestionConfig(min=1, max=5, ops=[OP_SUB, OP_SUB, OP_SUB])
    seen_negative = False
    for _ in range(300):
        _, result = generate_expression(cfg)
        if result < 0:
            seen_negative = True
            break
    assert seen_negative, "Subtraction chain should be able to produce negative results"


# ── generate_math_question ────────────────────────────────────────────────────


def test_generate_returns_required_keys():
    q = generate_math_question(1)
    assert "content" in q
    assert "correct_answer" in q


def test_generate_content_ends_with_equals_question():
    for level in [1, 5, 15, 30, 50, 94]:
        q = generate_math_question(level)
        assert q["content"].endswith("= ?"), f"Level {level}: '{q['content']}'"


def test_generate_correct_answer_is_int():
    for level in [1, 5, 15, 30, 50, 94]:
        q = generate_math_question(level)
        assert isinstance(q["correct_answer"], int), (
            f"Level {level}: answer type is {type(q['correct_answer'])}"
        )


def test_generate_answer_matches_pemdas_evaluation():
    for level in range(1, 95, 5):
        for _ in range(10):
            q = generate_math_question(level)
            tokens = q["content"].replace(" = ?", "").split()
            nums = [int(t) for t in tokens[::2]]
            ops = tokens[1::2]
            expected = _eval_pemdas(nums, ops)
            assert q["correct_answer"] == expected, (
                f"Level {level}: '{q['content']}' → expected {expected}, got {q['correct_answer']}"
            )


def test_generate_level_1_content_only_addition():
    for _ in range(50):
        q = generate_math_question(1)
        assert "+" in q["content"]
        assert "-" not in q["content"]
        assert "×" not in q["content"]
        assert "÷" not in q["content"]


def test_generate_below_sub_threshold_no_subtraction():
    for level in range(1, OP_SUB_LEVEL_START):
        for _ in range(20):
            q = generate_math_question(level)
            assert "-" not in q["content"], (
                f"Level {level}: unexpected − in '{q['content']}'"
            )


def test_generate_at_sub_threshold_can_produce_subtraction():
    seen = False
    for _ in range(300):
        if "-" in generate_math_question(OP_SUB_LEVEL_START)["content"]:
            seen = True
            break
    assert seen, f"Level {OP_SUB_LEVEL_START} never produced −"


def test_generate_below_mul_threshold_no_multiply_or_divide():
    for level in range(1, OP_MUL_OR_DIV_LEVEL_START):
        for _ in range(20):
            q = generate_math_question(level)
            assert "×" not in q["content"], f"Level {level}: unexpected × in '{q['content']}'"
            assert "÷" not in q["content"], f"Level {level}: unexpected ÷ in '{q['content']}'"


def test_generate_at_mul_threshold_can_produce_mul_or_div():
    seen = False
    for _ in range(300):
        q = generate_math_question(OP_MUL_OR_DIV_LEVEL_START)
        if "×" in q["content"] or "÷" in q["content"]:
            seen = True
            break
    assert seen, f"Level {OP_MUL_OR_DIV_LEVEL_START} never produced × or ÷"


def test_generate_at_both_mul_div_threshold_can_produce_each():
    seen_mul = seen_div = False
    for _ in range(500):
        q = generate_math_question(OP_MUL_AND_DIV_LEVEL_START)
        if "×" in q["content"]:
            seen_mul = True
        if "÷" in q["content"]:
            seen_div = True
        if seen_mul and seen_div:
            break
    assert seen_mul, f"Level {OP_MUL_AND_DIV_LEVEL_START} never produced ×"
    assert seen_div, f"Level {OP_MUL_AND_DIV_LEVEL_START} never produced ÷"


def test_generate_content_never_uses_ascii_mul_or_div():
    # Must use Unicode × ÷, never * or /
    for level in range(15, 60, 5):
        for _ in range(20):
            content = generate_math_question(level)["content"]
            assert "*" not in content, f"Level {level}: ASCII * in '{content}'"
            assert "/" not in content, f"Level {level}: ASCII / in '{content}'"


def test_generate_num_ops_follows_difficulty_formula():
    for level, expected_ops in [(1, 1), (14, 1), (15, 2), (29, 2), (30, 3), (44, 3), (45, 4)]:
        for _ in range(20):
            tokens = generate_math_question(level)["content"].replace(" = ?", "").split()
            actual_ops = len(tokens) // 2
            assert actual_ops == expected_ops, (
                f"Level {level}: expected {expected_ops} ops, got {actual_ops}"
            )


def test_generate_division_always_produces_exact_integer():
    # _eval_pemdas uses integer division; if it matches correct_answer, division is exact
    for level in range(1, 95):
        for _ in range(5):
            q = generate_math_question(level)
            tokens = q["content"].replace(" = ?", "").split()
            nums = [int(t) for t in tokens[::2]]
            ops = tokens[1::2]
            assert q["correct_answer"] == _eval_pemdas(nums, ops)
