"""Glitch Gate v0.2: a *teaching* clock-timing and software-fault abstraction.

This is NOT a ChipWhisperer emulator, hardware measurement, RTL simulator, or an
instruction-accurate CPU model. The numeric constants are illustrative.

The virtual glitch is an extra early rising edge followed by a high pulse.
- ext_offset selects the virtual cycle relative to a trigger.
- offset_ns (<0) locates the early edge relative to the nominal edge.
- width_ns is the inserted pulse's high duration.

An effective early edge shortens the sampling interval. A sampled failure-flag
write is *assumed* to be missed if it violates setup and the disruption is not
severe. This mapping is explicitly an instructional fault model: setup-time
violation by itself does not prove that a physical processor skips an opcode.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

EXPECTED_PASSWORD = "touch"
WRONG_PASSWORDS = ("toucX", "touXh", "toXch", "tXuch", "Xouch")

# Every time-related constant is in MODEL nanoseconds, not actual hardware data.
PERIOD_NS = 10.0
SETUP_NS = 0.60
FLAG_UPDATE_PATH_NS = 8.45
# Illustrative timing assumptions, not hardware measurements.
FLAG_PATH_BY_POSITION_NS = (8.05, 8.25, 8.45, 8.65, 8.85)
COMPARE_PATH_NS = 6.20
RETURN_PATH_NS = 6.00
IDLE_PATH_NS = 4.50
MIN_PULSE_WIDTH_NS = 0.75
MAX_RECOVERABLE_DEFICIT_NS = 0.70
# Pulse touching the nominal edge is treated as clock corruption/reset.
EDGE_GUARD_NS = 0.10
BASE_COMPARE_CYCLE = 2
CYCLES_PER_CHAR = 2
FLAG_DELAY_CYCLES = 1
BASE_RETURN_CYCLE = 12
MAX_CYCLE_SHIFT = 8
MAX_EXT_OFFSET = 20


@dataclass(frozen=True)
class GlitchSettings:
    width_ns: float
    offset_ns: float
    ext_offset: int


@dataclass(frozen=True)
class Operation:
    cycle: int
    name: str
    detail: str
    path_delay_ns: float
    security_sensitive: bool = False


@dataclass(frozen=True)
class AttemptResult:
    status: str                       # NORMAL, RESET, SUCCESS
    access_granted: bool
    explanation: str
    settings: Optional[GlitchSettings]
    operation: Operation
    effective_interval_ns: float
    required_interval_ns: float
    slack_ns: float                   # negative = timing violation
    fault_effect: str
    pulse_registered: bool
    baseline: bool = False


def _validate_password(password: str) -> None:
    if password not in WRONG_PASSWORDS:
        raise ValueError("Use one of the supplied one-character-wrong passwords.")


def failure_flag_cycle(password: str, cycle_shift: int = 0) -> int:
    """The update cycle for the only wrong character, derived from the trace."""
    _validate_password(password)
    if not isinstance(cycle_shift, int) or not 0 <= cycle_shift <= MAX_CYCLE_SHIFT:
        raise ValueError(f"cycle_shift must be an integer from 0 through {MAX_CYCLE_SHIFT}")
    mismatch = next(i for i, (got, exp) in enumerate(zip(password, EXPECTED_PASSWORD)) if got != exp)
    return BASE_COMPARE_CYCLE + CYCLES_PER_CHAR * mismatch + FLAG_DELAY_CYCLES + cycle_shift


def program_trace(password: str, cycle_shift: int = 0) -> list[Operation]:
    """A virtual operation sequence. The only failure write is for the mismatch."""
    _validate_password(password)
    # Validate shift even if caller does not request the failure cycle.
    failure_flag_cycle(password, cycle_shift)
    ops = [Operation(0 + cycle_shift, "START", "Begin password check", IDLE_PATH_NS),
           Operation(1 + cycle_shift, "INIT", "Set passok = 1", IDLE_PATH_NS)]
    for i, (got, exp) in enumerate(zip(password, EXPECTED_PASSWORD)):
        compare_cycle = BASE_COMPARE_CYCLE + CYCLES_PER_CHAR * i + cycle_shift
        ops.append(Operation(compare_cycle, f"COMPARE {i}",
                             f"Compare input[{i}] ({got}) with expected[{i}] ({exp})",
                             COMPARE_PATH_NS))
        if got != exp:
            ops.append(Operation(compare_cycle + FLAG_DELAY_CYCLES, "FAILURE WRITE",
                                 "Set passok = 0 because the character is wrong",
                                 FLAG_PATH_BY_POSITION_NS[i], True))
    ops.append(Operation(BASE_RETURN_CYCLE + cycle_shift, "RETURN", "Return passok", RETURN_PATH_NS))
    return sorted(ops, key=lambda op: op.cycle)


def operation_at(password: str, cycle_shift: int, cycle: int) -> Operation:
    for op in program_trace(password, cycle_shift):
        if op.cycle == cycle:
            return op
    return Operation(cycle, "IDLE", "No modeled critical operation on this cycle", IDLE_PATH_NS)


def _result(status: str, description: str, settings: Optional[GlitchSettings],
            op: Operation, interval: float, required: float, effect: str,
            registered: bool, baseline: bool = False) -> AttemptResult:
    return AttemptResult(status, status == "SUCCESS", description, settings,
                         op, interval, required, interval - required, effect,
                         registered, baseline)


def run_baseline(password: str = WRONG_PASSWORDS[0], cycle_shift: int = 0) -> AttemptResult:
    """Correct execution of the toy password program; intentionally wrong input."""
    ops = program_trace(password, cycle_shift)
    op = next(item for item in ops if item.security_sensitive)
    required = op.path_delay_ns + SETUP_NS
    return _result("NORMAL", "Without an injected edge, the wrong character sets passok = 0, so access is denied.",
                   None, op, PERIOD_NS, required, "None: ordinary password rejection", False, baseline=True)


def inject(settings: GlitchSettings, password: str = WRONG_PASSWORDS[0],
           cycle_shift: int = 0) -> AttemptResult:
    """Apply documented illustrative pulse/timing constraints and a fault policy."""
    _validate_password(password)
    if not 0.0 < settings.width_ns <= 5.0:
        raise ValueError("width_ns must be >0 and <=5 model ns")
    if not -5.0 <= settings.offset_ns < 0.0:
        raise ValueError("offset_ns must be >=-5 and <0 model ns")
    if not isinstance(settings.ext_offset, int) or not 0 <= settings.ext_offset <= MAX_EXT_OFFSET:
        raise ValueError(f"ext_offset must be an integer from 0 through {MAX_EXT_OFFSET}")

    op = operation_at(password, cycle_shift, settings.ext_offset)
    required = op.path_delay_ns + SETUP_NS

    # A too-narrow pulse cannot reliably be captured by this toy flip-flop.
    if settings.width_ns < MIN_PULSE_WIDTH_NS:
        return _result("NORMAL", "The inserted high pulse is shorter than the model's minimum width. "
                       "The extra edge is ignored; the wrong password is rejected.",
                       settings, op, PERIOD_NS, required, "Pulse rejected (no modeled fault)", False)

    early_edge = PERIOD_NS + settings.offset_ns
    early_distance = -settings.offset_ns  # gap between early and nominal edge
    interval = early_edge

    # Conservative model for a pulse that overlaps the nominal next edge.
    if settings.width_ns >= early_distance - EDGE_GUARD_NS:
        return _result("RESET", "The inserted pulse overlaps or nearly touches the nominal clock edge. "
                       "This simplified model treats the malformed waveform as a reset.",
                       settings, op, interval, required, "Overlapping clock pulse (assumed reset)", True)

    deficit = required - interval
    if deficit <= 0:
        return _result("NORMAL", "The shortened interval still satisfies the selected operation's "
                       "path delay plus setup-time requirement; access remains denied.",
                       settings, op, interval, required, "Timing requirement satisfied", True)

    if deficit > MAX_RECOVERABLE_DEFICIT_NS:
        return _result("RESET", "The sampling interval is far shorter than the selected operation's "
                       "required time. The teaching model labels a severe violation as RESET.",
                       settings, op, interval, required, "Severe timing violation (assumed reset)", True)

    if op.security_sensitive:
        return _result("SUCCESS", "A moderate setup-time violation occurs at the failure-flag update. "
                       "The teaching fault model assumes that update is missed: passok stays 1 "
                       "and the one-character-wrong password is accepted.",
                       settings, op, interval, required, "Missed passok = 0 update (modeled, not hardware-confirmed)", True)

    return _result("NORMAL", "The selected cycle experiences a small modeled timing violation, but "
                   "it is not the failure-flag update. The externally observed authentication result "
                   "is still rejection (NORMAL category).",
                   settings, op, interval, required, "Non-critical timing violation; no bypass", True)


def example_success_settings(password: str = WRONG_PASSWORDS[0], cycle_shift: int = 0) -> GlitchSettings:
    """For instructors/tests only. Do not display this as a hint during the challenge."""
    flag = next(
        op for op in program_trace(password, cycle_shift)
        if op.security_sensitive
    )
    offset = round(
        flag.path_delay_ns + SETUP_NS - PERIOD_NS - 0.55, 2
    )
    width = round(
        min(1.20, -offset - EDGE_GUARD_NS - 0.15), 2
    )
    return GlitchSettings(
        width_ns=width,
        offset_ns=offset,
        ext_offset=failure_flag_cycle(password, cycle_shift)
    )
