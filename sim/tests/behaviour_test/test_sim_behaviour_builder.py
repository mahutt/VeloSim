"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from sim.behaviour.sim_behaviour_builder import SimBehaviourBuilder
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.behaviour.resource_behaviour.resource_choose_next_task_strategy import (
    DriverChooseNextTaskStrategy,
)
from sim.behaviour.station_behaviour.strategies.task_popup_strategy import (
    TaskPopupStrategy,
)
from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy
from sim.behaviour.default.default_RCNT_strategy import DefaultRCNTStrategy


# Stub strategies for testing
class StubRCNTStrategy(DriverChooseNextTaskStrategy):
    def select_next_task(self, driver):  # type: ignore[no-untyped-def]
        return None


class StubTPUStrategy(TaskPopupStrategy):
    def check_for_new_task(self, station):  # type: ignore[no-untyped-def]
        return False


def test_builder_initializes_with_default_behaviour() -> None:
    """Test that builder starts with a fresh SimBehaviour instance"""
    builder = SimBehaviourBuilder()
    assert builder.sim_behaviour is not None
    assert isinstance(builder.sim_behaviour, SimBehaviour)


def test_set_RCNT_strategy_returns_self() -> None:
    """Test that set_RCNT_strategy returns the builder for method chaining"""
    builder = SimBehaviourBuilder()
    strategy = StubRCNTStrategy()
    result = builder.set_RCNT_strategy(strategy)
    assert result is builder


def test_set_TPU_strategy_returns_self() -> None:
    """Test that set_TPU_strategy returns the builder for method chaining"""
    builder = SimBehaviourBuilder()
    strategy = StubTPUStrategy()
    result = builder.set_TPU_strategy(strategy)
    assert result is builder


def test_set_RCNT_strategy_assigns_strategy() -> None:
    """Test that RCNT strategy is properly assigned to SimBehaviour"""
    builder = SimBehaviourBuilder()
    strategy = StubRCNTStrategy()
    builder.set_RCNT_strategy(strategy)
    assert builder.sim_behaviour.RCNT_strategy is strategy


def test_set_TPU_strategy_assigns_strategy() -> None:
    """Test that TPU strategy is properly assigned to SimBehaviour"""
    builder = SimBehaviourBuilder()
    strategy = StubTPUStrategy()
    builder.set_TPU_strategy(strategy)
    assert builder.sim_behaviour.TPU_strategy is strategy


def test_method_chaining() -> None:
    """Test that methods can be chained together"""
    builder = SimBehaviourBuilder()
    rcnt_strategy = StubRCNTStrategy()
    tpu_strategy = StubTPUStrategy()

    result = builder.set_RCNT_strategy(rcnt_strategy).set_TPU_strategy(tpu_strategy)

    assert result is builder
    assert builder.sim_behaviour.RCNT_strategy is rcnt_strategy
    assert builder.sim_behaviour.TPU_strategy is tpu_strategy


def test_get_sim_behaviour_returns_configured_behaviour() -> None:
    """Test that get_sim_behaviour returns the configured SimBehaviour"""
    builder = SimBehaviourBuilder()
    rcnt_strategy = StubRCNTStrategy()
    tpu_strategy = StubTPUStrategy()

    behaviour = (
        builder.set_RCNT_strategy(rcnt_strategy)
        .set_TPU_strategy(tpu_strategy)
        .get_sim_behaviour()
    )

    assert isinstance(behaviour, SimBehaviour)
    assert behaviour.RCNT_strategy is rcnt_strategy
    assert behaviour.TPU_strategy is tpu_strategy


def test_get_sim_behaviour_resets_builder() -> None:
    """Test that get_sim_behaviour resets the builder with a new SimBehaviour"""
    builder = SimBehaviourBuilder()
    rcnt_strategy = StubRCNTStrategy()

    # Configure and get first behaviour
    first_behaviour = builder.set_RCNT_strategy(rcnt_strategy).get_sim_behaviour()

    # Builder should have a new SimBehaviour instance
    assert builder.sim_behaviour is not first_behaviour
    assert isinstance(builder.sim_behaviour, SimBehaviour)


def test_reset_creates_new_sim_behaviour() -> None:
    """Test that reset() creates a new SimBehaviour instance"""
    builder = SimBehaviourBuilder()
    original_behaviour = builder.sim_behaviour

    builder.reset()

    assert builder.sim_behaviour is not original_behaviour
    assert isinstance(builder.sim_behaviour, SimBehaviour)


def test_reset_uses_default_strategies() -> None:
    """Test that reset() creates SimBehaviour with default strategies"""
    builder = SimBehaviourBuilder()
    builder.set_RCNT_strategy(StubRCNTStrategy())
    builder.set_TPU_strategy(StubTPUStrategy())

    builder.reset()

    # After reset, should have default strategies
    assert isinstance(builder.sim_behaviour.RCNT_strategy, DefaultRCNTStrategy)
    assert isinstance(builder.sim_behaviour.TPU_strategy, DefaultTPUStrategy)


def test_builder_reuse_after_get() -> None:
    """Test that builder can be reused after calling get_sim_behaviour"""
    builder = SimBehaviourBuilder()

    # Build first behaviour
    first_rcnt = StubRCNTStrategy()
    first_behaviour = builder.set_RCNT_strategy(first_rcnt).get_sim_behaviour()

    # Build second behaviour with different strategy
    second_rcnt = StubRCNTStrategy()
    second_behaviour = builder.set_RCNT_strategy(second_rcnt).get_sim_behaviour()

    # Should be different instances
    assert first_behaviour is not second_behaviour
    assert first_behaviour.RCNT_strategy is first_rcnt
    assert second_behaviour.RCNT_strategy is second_rcnt


def test_partial_configuration() -> None:
    """Test building SimBehaviour with only one strategy configured"""
    builder = SimBehaviourBuilder()
    rcnt_strategy = StubRCNTStrategy()

    behaviour = builder.set_RCNT_strategy(rcnt_strategy).get_sim_behaviour()

    # RCNT should be custom, TPU should be default
    assert behaviour.RCNT_strategy is rcnt_strategy
    assert isinstance(behaviour.TPU_strategy, DefaultTPUStrategy)


def test_empty_configuration() -> None:
    """Test getting SimBehaviour without configuring any strategies"""
    builder = SimBehaviourBuilder()
    behaviour = builder.get_sim_behaviour()

    # Should have default strategies
    assert isinstance(behaviour.RCNT_strategy, DefaultRCNTStrategy)
    assert isinstance(behaviour.TPU_strategy, DefaultTPUStrategy)
