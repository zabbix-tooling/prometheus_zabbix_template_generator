#!/usr/bin/env python3

import argparse

from prom2zabbix.parser import PrometheusExporterParser

parser = argparse.ArgumentParser()

parser.add_argument("--dump", "-c", help="a dumped prometheus exporter output", type=str, required=False)
parser.add_argument("--template", "-t", help="A zabbix template which uses the reserved markers", type=str,
                    required=False, default=None)
parser.add_argument("--name", "-n", help="A zabbix template template name", type=str,
                    required=False, default=None)

args = parser.parse_args()

if args.dump:
    with open(args.dump, "r") as f:
        prom_dump_lines = f.readlines()
        prom_parser = PrometheusExporterParser(lines=prom_dump_lines, example_template=args.template)

prom_parser.parse()

prom_parser.generate_template(args.name)
prom_parser.get_stats()
