from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models.power import PDU, UPS, PowerFeed


def load_pdus(path: Path = Path("doctrine/power/pdu.yaml")) -> list[PDU]:
    data = load_yaml_file(path)
    return [PDU(**entry) for entry in data]

def load_ups(path: Path = Path("doctrine/power/ups.yaml")) -> list[UPS]:
    data = load_yaml_file(path)
    return [UPS(**entry) for entry in data]

def load_feeds(path: Path = Path("doctrine/power/feeds.yaml")) -> list[PowerFeed]:
    data = load_yaml_file(path)
    return [PowerFeed(**entry) for entry in data]

pdus = load_pdus()
ups = load_ups()
feeds = load_feeds()
