import os
import yaml
import datetime
from typing import (
    Any,
    Dict,
    Union,
    Optional,
)

from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)

from epics import PV
from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator,
)
import numpy as np
from lcls_tools.common.devices.screen import Screen, ScreenCollection


DEFAULT_YAML_LOCATION = "./lcls_tools/common/devices/yaml/"


def _find_yaml_file(area: str = None, beampath: Optional[str] = None) -> str:
    if area:
        filename = area + ".yaml"
    if beampath:
        filename = "beampaths.yaml"

    path = os.path.join(DEFAULT_YAML_LOCATION, filename)
    if os.path.isfile(path):
        return os.path.abspath(path)
    else:
        raise FileNotFoundError(
            f"No such file {path}, please choose another area.",
        )


def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    if area:
        try:
            location = _find_yaml_file(
                area=area,
            )
            with open(location, "r") as device_file:
                config_data = yaml.safe_load(device_file)
                if name:
                    magnet_data = config_data["magnets"][name]
                    # this data is not available from YAML directly in this form, so we add it here.
                    magnet_data.update({"name": name})
                    return Magnet(**magnet_data)
                else:
                    return MagnetCollection(**config_data)
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None
        except KeyError:
            print(f"Could not find name {name} in file for area: {area}")
            return None
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        print("Please provide a machine area to create a magnet from.")
        return None
    

def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    device_data = _device_or_collection(area=area, name=name)
    try:
        magnet_data = device_data["magnets"][name]
        # this data is not available from YAML directly in this form, so we add it here.
        magnet_data.update({"name": name})
        return Magnet(**magnet_data)
    except:
        return MagnetCollection(**device_data)


def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    device_data = _device_or_collection(area=area, name=name)
    try:
        magnet_data = device_data["magnets"][name]
        # this data is not available from YAML directly in this form, so we add it here.
        magnet_data.update({"name": name})
        return Magnet(**magnet_data)
    except:
        return MagnetCollection(**device_data)


def create_screen(
    area: str = None, name: str = None
) -> Union[None, Screen, ScreenCollection]:
    if area:
        try:
            location = _find_yaml_file(
                area=area,
            )
            with open(location, "r") as device_file:
                config_data = yaml.safe_load(device_file)
                if name:
                    screen_data = config_data["screens"][name]
                    # this data is not available from YAML directly in this form, so we add it here.
                    screen_data.update({"name": name})
                    return Screen(**screen_data)
                else:
                    return ScreenCollection(**config_data)
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None
        except KeyError:
            print(f"Could not find name {name} in file for area: {area}")
            return None
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        print("Please provide a machine area to create a magnet from.")
        return None

