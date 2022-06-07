import click
import httpx
import time
import pathlib
import json


@click.command()
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True))
@click.option("save_stats", "--stats", is_flag=True, help="Also write out stats")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def scrape_socrata(directory, save_stats, verbose):
    "Scrape all of Socrata for dataset listings and write results to directory"
    domain_files = {}
    stats_files = {}
    root = pathlib.Path(directory)
    if not root.exists():
        root.mkdir(parents=True)
    for record in fetch_all(verbose):
        stats = {"id": record["resource"]["id"], "stats": {}}
        if "page_views" in record["resource"]:
            stats["stats"].update(record["resource"].pop("page_views"))
        stats["stats"]["download_count"] = record["resource"].pop("download_count")
        domain = record["metadata"]["domain"]
        if domain not in domain_files:
            domain_files[domain] = (root / "{}.jsonl".format(domain)).open("w")
        domain_files[domain].write(json.dumps(record) + "\n")
        if save_stats:
            if domain not in stats_files:
                stats_files[domain] = (root / "{}.stats.json".format(domain)).open("w")
            stats_files[domain].write(json.dumps(stats) + "\n")


def fetch_all(verbose=False):
    base_url = (
        "http://api.us.socrata.com/api/catalog/v1?limit=1000&only=dataset&only=calendar"
    )
    scroll_id = None
    while True:
        url = base_url
        if scroll_id is not None:
            url = base_url + "&scroll_id=" + scroll_id
        if verbose:
            click.echo(url, err=True)
        data = httpx.get(url).json()
        results = data["results"]
        if not results:
            break
        scroll_id = results[-1]["resource"]["id"]
        yield from results
        time.sleep(0.5)


if __name__ == "__main__":
    scrape_socrata()
