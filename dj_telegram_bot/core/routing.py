from __future__ import annotations

import functools
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from types import MethodType
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)


Mode = Literal["prefix", "suffix", "contains", "any"]


def parse_wildcard(trigger: str) -> tuple[Mode, str] | None:
    if "*" not in trigger:
        return None

    if trigger == "*":
        return "any", ""

    literal = trigger.strip("*")
    if not literal or "*" in literal:
        raise ValueError(f"Unsupported wildcard trigger: {trigger}")

    starts, ends = trigger.startswith("*"), trigger.endswith("*")
    if starts and ends:
        return "contains", literal

    return ("prefix", literal) if ends else ("suffix", literal)


@dataclass(frozen=True, slots=True)
class Route:
    """
    Holds everything needed to run one handler, in a single object.

        @message_handler("buy_*")
        def buy(h): ...        ->   Route(trigger="buy_*", func=buy)

    Where it is used:
        update arrives -> Router.find() picks the matching Route
                       -> BaseHandler._execute() calls its function
    """

    trigger: str
    func: Callable[..., Any]
    owner: type | None = None
    name: str | None = None
    priority: int = 0
    step: bool = False
    wildcard: tuple[Mode, str] | None = field(init=False, default=None)

    def __post_init__(self):
        wildcard = None if self.step else parse_wildcard(self.trigger)
        object.__setattr__(self, "wildcard", wildcard)

    @property
    def is_method(self) -> bool:
        return self.owner is not None

    @property
    def specificity(self) -> tuple[int, int]:
        """Sort key for wildcards: explicit priority first, then literal length."""
        return self.priority, len(self.wildcard[1]) if self.wildcard else 0

    def matches(self, key: str) -> bool:
        if not self.wildcard:
            return False

        mode, literal = self.wildcard
        if mode == "any":
            return True

        if mode == "contains":
            return literal in key

        if mode == "prefix":
            return key.startswith(literal)

        return key.endswith(literal)  # suffix


@dataclass(frozen=True)
class _Binding:
    """
    A to-do note left by a decorator: "register this function under this rule".

        @message_handler("buy_*")   ->   _Binding("message", "buy_*")
        def buy(h): ...

    Decorators run while the module is loading, before we know whether the
    function sits inside a class (a Route needs that). So the note waits in the
    Router, and Router.build() later turns each one into a real Route.
    """

    handler_type: str
    trigger: str
    priority: int = 0
    step: bool = False


class _RouteDescriptor:
    """
    Lets us tell whether a decorated function is a plain function or a method.

    The decorator wraps the function in this object.
    If the function sits inside a class, Python automatically calls
    __set_name__ on it, and that is how we find out.

        @message_handler("buy")
        def buy(h): ...                  # no __set_name__ call -> plain function

        class Shop(BaseHandler):
            @message_handler("buy")
            def buy(self): ...           # __set_name__(Shop, "buy") -> method
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func
        self.owner: type | None = None
        self.name: str | None = None
        self.bindings: list[_Binding] = []
        functools.update_wrapper(self, func, updated=())

    def add(self, router: Router, binding: _Binding) -> None:
        if binding in self.bindings:
            return

        if not binding.step:  # Validate the trigger
            parse_wildcard(binding.trigger)

        self.bindings.append(binding)
        router.defer(self, binding)

    def make_route(self, binding: _Binding) -> Route:
        return Route(
            binding.trigger,
            self.func,
            self.owner,
            self.name,
            binding.priority,
            binding.step,
        )

    def __get__(self, instance, owner=None):
        return self if instance is None else MethodType(self.func, instance)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner, self.name = owner, name


class Router:
    """
    Decides which handler function should run for an incoming update.

    Every function registered with a decorator ends up in a Router.
    When an update arrives, we ask the Router to find the match:

        router.find("message", "buy_5")   ->   the Route registered for "buy_*"

    It checks in this order and returns the first match, or None if nothing
    matches:
        1. an exact match (e.g. "start")
        2. the user's current step (e.g. "ask_name")
        3. a wildcard (e.g. "buy_*"); if several match(overlap), higher priority wins

    Decorators don't add routes directly. They leave _Binding notes, and
    build() later turns those notes into Routes (see _Binding for why).
    """

    def __init__(self) -> None:
        self._steps: dict[str, dict[str, Route]] = defaultdict(dict)
        self._exact: dict[str, dict[str, Route]] = defaultdict(dict)
        self._wildcards: dict[str, list[Route]] = defaultdict(list)
        self._pending: list[tuple[_RouteDescriptor, _Binding]] = []

    def defer(self, desc: _RouteDescriptor, binding: _Binding) -> None:
        self._pending.append((desc, binding))

    def build(self) -> None:
        """Turn queued descriptors into routes. Safe to call many times."""
        pending, self._pending = self._pending, []
        for desc, binding in pending:
            self.register(binding.handler_type, desc.make_route(binding))

    def register(self, handler_type: str, route: Route) -> None:
        if route.wildcard:
            self._register_wildcard(handler_type, route)
            return

        table = self._steps if route.step else self._exact
        bucket = table[handler_type]
        self._warn_if_overridden(handler_type, bucket.get(route.trigger), route)
        bucket[route.trigger] = route

    def _register_wildcard(self, handler_type: str, route: Route) -> None:
        bucket = self._wildcards[handler_type]
        old = next((r for r in bucket if r.trigger == route.trigger), None)
        if old:
            self._warn_if_overridden(handler_type, old, route)
            bucket.remove(old)

        bucket.append(route)
        # sort is stable: equal specificity keeps registration order
        bucket.sort(key=lambda r: r.specificity, reverse=True)

    @staticmethod
    def _warn_if_overridden(handler_type: str, old: Route | None, new: Route) -> None:
        if old and old.func is not new.func:
            logger.warning("Pattern %r in %s overridden", new.trigger, handler_type)

    def find(self, handler_type: str, key: str, step: str = "") -> Route | None:
        self.build()

        exact = self._exact.get(handler_type, {})
        if route := exact.get(key):
            return route

        steps = self._steps.get(handler_type, {})
        if step and (route := steps.get(step)):
            return route

        wildcards = self._wildcards.get(handler_type, ())
        return next((r for r in wildcards if r.matches(key)), None)

    def clear(self) -> None:
        """Drop everything (useful for testing)."""
        self._steps.clear()
        self._exact.clear()
        self._wildcards.clear()
        self._pending.clear()


default_router = Router()


def make_decorator(
    handler_type: str, *, router: Router | None = None, step: bool = False
):
    router = router or default_router
    label = f"{handler_type}{'_step' if step else ''}_handler"

    def factory(trigger: str, *, priority: int = 0):
        if not isinstance(trigger, str):
            raise TypeError(f"@{label} needs a trigger: use @{label}('...')")

        def decorator(obj):
            desc = obj if isinstance(obj, _RouteDescriptor) else _RouteDescriptor(obj)
            desc.add(router, _Binding(handler_type, trigger, priority, step))
            return desc

        return decorator

    return factory


command_handler = make_decorator("command")
message_handler = make_decorator("message")
callback_handler = make_decorator("callback")
inline_handler = make_decorator("inline")
chosen_handler = make_decorator("chosen")

# match on the user's step instead of the incoming text/data
message_step_handler = make_decorator("message", step=True)
callback_step_handler = make_decorator("callback", step=True)
