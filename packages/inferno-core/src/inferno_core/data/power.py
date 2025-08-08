from pathlib import Path

from inferno_core.data.loader import load_yaml_file, load_yaml_list
from inferno_core.models.power import PDU, UPS, PowerFeed


def load_pdus(path: Path = Path("doctrine/power/pdu.yaml")) -> list[PDU]:
    return load_yaml_list(path, PDU)


def load_ups(path: Path = Path("doctrine/power/ups.yaml")) -> list[UPS]:
    return load_yaml_list(path, UPS)

def load_feeds(path: Path = Path("doctrine/power/feeds.yaml")) -> list[PowerFeed]:
    return load_yaml_list(path, PowerFeed)

pdus = load_pdus()
ups = load_ups()
feeds = load_feeds()
