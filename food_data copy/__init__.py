"""Food data module - imports all state food datasets."""

from .kerala_food import kerala_food
from .tamil_nadu_food import tamil_nadu_food
from .delhi_food import delhi_food
from .haryana_food import haryana_food
from .himachal_pradesh_food import himachal_pradesh_food
from .jammu_kashmir_food import jammu_kashmir_food
from .jharkhand_food import jharkhand_food
from .uttarakhand_food import uttarakhand_food
from .punjab_food import punjab_food
from .rajasthan_food import rajasthan_food
from .uttar_pradesh_food import uttar_pradesh_food
from .bihar_food import bihar_food
from .karnataka_food import karnataka_food
from .andhra_pradesh_food import andhra_pradesh_food
from .telangana_food import telangana_food
from .western_food import western_food
from .snacks import snacks

# Mapping state names to their food datasets
STATE_FOOD_MAPPING = {
    "Kerala": kerala_food,
    "Tamil Nadu": tamil_nadu_food,
    "Karnataka": karnataka_food,
    "Andhra Pradesh": andhra_pradesh_food,
    "Telangana": telangana_food,
    "Delhi": delhi_food,
    "Punjab": punjab_food,
    "Haryana": haryana_food,
    "Uttar Pradesh": uttar_pradesh_food,
    "Uttarakhand": uttarakhand_food,
    "Himachal Pradesh": himachal_pradesh_food,
    "Jammu and Kashmir": jammu_kashmir_food,
    "Jharkhand": jharkhand_food,
    "Rajasthan": rajasthan_food,
    "Bihar": bihar_food,
    "Western": western_food
}

__all__ = [
    'kerala_food',
    'tamil_nadu_food',
    'delhi_food',
    'haryana_food',
    'himachal_pradesh_food',
    'jammu_kashmir_food',
    'jharkhand_food',
    'uttarakhand_food',
    'punjab_food',
    'rajasthan_food',
    'uttar_pradesh_food',
    'bihar_food',
    'karnataka_food',
    'andhra_pradesh_food',
    'telangana_food',
    'western_food',
    'snacks',
    'STATE_FOOD_MAPPING',
]

