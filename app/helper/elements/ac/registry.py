from __future__ import annotations

from app.helper.elements.registry import ElementsRegistry

from .bus import BusHandler
from .ext_grid import ExtGridHandler
from .gen import GenHandler
from .line import LineHandler
from .load import LoadHandler
from .motor import MotorHandler
from .sgen import SGenHandler
from .shunt import ShuntHandler
from .storage import StorageHandler
from .switch import SwitchHandler
from .trafo import TrafoHandler
from .trafo3w import Trafo3WHandler
from .ward import WardHandler


def build_ac_registry() -> ElementsRegistry:
    r = ElementsRegistry()
    r.register(BusHandler())
    r.register(ExtGridHandler())
    r.register(LineHandler())
    r.register(LoadHandler())
    r.register(GenHandler())
    r.register(SGenHandler())
    r.register(TrafoHandler())
    r.register(Trafo3WHandler())
    r.register(MotorHandler())
    r.register(StorageHandler())
    r.register(ShuntHandler())
    r.register(WardHandler())
    r.register(SwitchHandler())
    return r


