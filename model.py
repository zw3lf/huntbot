import abc
from abc import ABC
from collections import defaultdict
from enum import Enum, auto
from typing import Dict, List, Optional, Type

DiscordRole = str


class Expacs(Enum):
    ARR = auto()
    HW = auto()
    SB = auto()
    SHB = auto()
    EW = auto()
    # DT = auto()


class Currencies(Enum):
    ALLIED = auto()
    CENTURIO = auto()
    NUTS = auto()


currency_to_expac_mapping = {
    Currencies.ALLIED: [Expacs.ARR],
    Currencies.CENTURIO: [Expacs.HW, Expacs.SB],
    Currencies.NUTS: [Expacs.SHB, Expacs.EW]
}

expac_to_currency_mapping: Dict[Expacs, List[Currencies]] = defaultdict(list)

for k, v in currency_to_expac_mapping.items():
    for vv in v:
        expac_to_currency_mapping[vv].append(k)


class RoleResolver(ABC):
    @abc.abstractmethod
    def role_for_expac(self, expac: Expacs) -> bool:
        """Return true if the expac for the selected train matches the role's desires"""
        pass


class ExpacRoleResolver(RoleResolver):
    """
    Roles based on expansion packs
    """

    def __init__(self, role_mappings: Dict[Expacs, DiscordRole]):
        self.roles = role_mappings

    def role_for_expac(self, expac: Expacs):
        return expac in self.roles


class CurrencyRoleResolver(RoleResolver):
    """
    Roles based on currencies train gives
    """

    def __init__(self, role_mappings: Dict[Currencies, DiscordRole]):
        self.roles = role_mappings

    def role_for_expac(self, expac: Expacs):
        return expac_to_currency_mapping[expac] in self.roles


class SingularRoleResolver(RoleResolver):
    """
    One role used for all trains
    """

    def __init__(self, role):
        self.role = role

    def role_for_expac(self, expac: Expacs):
        return True


class DiscordTarget:
    def __init__(self, webhook_url: str, roles: RoleResolver):
        self.webhook_url: str = webhook_url
        self.roles: RoleResolver = roles


def resolve_role(role_key: str) -> Type[RoleResolver]:
    """
    Envvar format is ROLE[_<EXPAC/CURRENCY>]_<NAME>
    If the middle section is missing then all trains are advertised with the one role

    :param role_key: The Envvar to be parsed and resolved
    :return: A RoleResolver class that will be instantiated by the caller
    """
    splat = role_key.split('_')
    if len(splat) == 2:
        return SingularRoleResolver
    elif len(splat) == 3:
        if splat[1] in Expacs.__members__.keys():
            return ExpacRoleResolver
        if splat[1] in Currencies.__members__.keys():
            return CurrencyRoleResolver
    raise Exception(f"Unable to resolve role type for envvar {role_key}")
