#!/usr/bin/env python3

import argparse

from prometheus_zabbix_template_generator.parser import PrometheusExporterParser
import requests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--template", "-t", help="A zabbix template which uses the reserved markers", type=str,
                        required=False, default=None)

    # you have to provdide either --dump or --url
    parser.add_argument("--dump", "-c", help="a dumped prometheus exporter output", type=str,
                        required=False, default=None)
    parser.add_argument("--url", "-u", help="A zabbix template which uses the reserved markers", type=str,
                        required=False, default=None)

    parser.add_argument("--name", "-n", help="A zabbix template template name", type=str,
                        required=False, default=None)

    args = parser.parse_args()

    if not args.dump and not args.url:
        parser.error("You have to define either --dump or --url")

    if args.dump:
        with open(args.dump, "r") as f:
            prom_dump_lines = f.readlines()
            prom_parser = PrometheusExporterParser(lines=prom_dump_lines, example_template=args.template)
    if args.url:
        r = requests.get(args.url)
        r.raise_for_status()
        prom_dump_lines = r.text.split("\n")
        prom_parser = PrometheusExporterParser(lines=prom_dump_lines, example_template=args.template)

    prom_parser.parse()
    prom_parser.generate_template(args.name)
    prom_parser.get_stats()
