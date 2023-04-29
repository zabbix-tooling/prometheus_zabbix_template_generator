import copy
import json
import re
from dataclasses import dataclass, field
from enum import Enum
import datetime

import uuid as uuid


class ParserState(Enum):
    START = 1
    NEW_GROUP = 2
    TYPE = 3
    METRICS = 4


class ItemType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    SUMMARY = "summary"


@dataclass
class ZabbixItem:
    """Class for keeping track of an item in inventory."""
    base_label: str = None
    label: str = ""
    type: str = None
    help: str = None
    examples: list[str] = field(default_factory=list)

    def __str__(self):
        return f"TYPE {self.type} => {self.label}"

    def _get_item_definition(self, item_template: dict, name: str, template_uuid: str) -> dict:
        new_item = copy.deepcopy(item_template)
        new_item["uuid"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, name + template_uuid)).replace("-", "")
        new_item["description"] = self.help
        new_item["key"] = new_item["key"].replace("PROM2ZABBIX_ITEM_KEY", self.label)
        new_item["name"] = new_item["name"].replace("PROM2ZABBIX_ITEM_NAME", self.label)
        return new_item


class PrometheusExporterParser:

    def __init__(self, lines: list[str], example_template: str = None):
        self.lines = lines
        self.state: ParserState = ParserState.START
        self.collected_items: dict[str, ZabbixItem] = {}
        if example_template:
            with open(example_template, "r") as f:
                self.example_template = json.load(f)

    def parse(self):
        item: ZabbixItem = None
        for line_nr, line_str in enumerate(self.lines):
            line_str = line_str.strip()
            if self.state in [ParserState.START, ParserState.METRICS]:
                m = re.fullmatch(r'# HELP (.+)$', line_str)
                if m:
                    self.state = ParserState.NEW_GROUP
                    item = ZabbixItem(help=m.group(1))
                    continue
            if self.state == ParserState.NEW_GROUP:
                m = re.fullmatch(r'# TYPE (.+) (.+)$', line_str)
                if m:
                    self.state = ParserState.TYPE
                    item.base_label = m.group(1)
                    item.type = ItemType(m.group(2))
                    continue
            if self.state in [ParserState.TYPE, ParserState.METRICS]:
                regex = "(?P<prefix>%s.*?)(?P<labels>{.+?})? (?P<example_value>.+)$" % item.base_label
                m = re.fullmatch(regex, line_str)
                if m:
                    self.state = ParserState.METRICS
                    item.label = (m.group("prefix") or "") + \
                                 (m.group("labels") or "")
                    item.examples.append(m.group("example_value"))
                    self.collected_items[item.label] = copy.deepcopy(item)
                    print(item)
                    continue

            raise RuntimeError(f"Unknown state {self.state} for line >>>{line_str}<<< in line number {line_nr}")

    def generate_template(self, name: str | None):
        file_name = None
        if name:
            template_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, name)).replace("-", "")
            file_name = f"{name}.json".replace(" ", "_")
        else:
            template_uuid = None

        new_template = copy.deepcopy(self.example_template)
        new_template["zabbix_export"]["date"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if name:
            new_template["zabbix_export"]["templates"][0]["name"] = \
                new_template["zabbix_export"]["templates"][0]["name"] \
                    .replace("PROM2ZABBIX_TEMPLATE_NAME", name.title())
            new_template["zabbix_export"]["templates"][0]["template"] = \
                new_template["zabbix_export"]["templates"][0]["template"] \
                    .replace("PROM2ZABBIX_TEMPLATE_NAME", name) \
                    .replace(" ", "_").lower()
        else:
            name = "DEFAULT"

        item_template = new_template["zabbix_export"]["templates"][0]["items"][0]

        new_template["zabbix_export"]["templates"][0]["items"] = []
        for item in self.collected_items.values():
            new_template["zabbix_export"]["templates"][0]["items"].append(
                item._get_item_definition(
                    item_template=item_template,
                    name=name,
                    template_uuid=template_uuid)
            )

        if file_name:
            with open(file_name, "w") as f:
                print("Writing template to", file_name)
                json.dump(new_template, f, indent=2)

    def get_stats(self):
        print("*" * 80)
        print("Stats:")
        print(f"found {len(self.collected_items.keys())} items")
        item_types = {}
        for item in self.collected_items.values():
            item_types.setdefault(item.type, 0)
            item_types[item.type] += 1
        for key, value in item_types.items():
            print(f"{key}: {value}")
        print("*" * 80)
