from re import I
import click
import sqlite_utils
import pathlib
import json


@click.command()
@click.argument("db_path", type=click.Path(file_okay=True, dir_okay=False))
@click.argument(
    "directory", type=click.Path(file_okay=False, dir_okay=True, exists=True)
)
def build_db(db_path, directory):
    "Build a SQLite database from the jsonl files in the directory"
    root = pathlib.Path(directory)
    db = sqlite_utils.Database(db_path)
    with db.conn:
        all_files = list(root.glob("*.jsonl"))
        # Sort them so the stats ones come after the main ones
        all_files.sort(key=lambda f: ('.stats.' in f.name, f.name))
        with click.progressbar(all_files) as files:
            for jsonl in files:
                if ".stats." in jsonl.name:
                    db["resources"].upsert_all(_stats(jsonl), pk="id", alter=True)
                else:
                    db["resources"].upsert_all(
                        _docs(jsonl),
                        pk="id",
                        alter=True,
                        column_order=("id", "domain", "link", "name", "description"),
                    )
    # Delete anything with 'link is null', which means that it was in a stats file but
    # had been removed from the regular file
    db["resources"].delete_where("link is null")
    # Enable search
    db["resources"].enable_fts(
        ["name", "description", "columns_name", "columns_description"]
    )


def _docs(file):
    for line in file.open():
        if line.strip():
            raw = json.loads(line)
            record = {
                "id": raw["resource"]["id"],
                "domain": raw["metadata"]["domain"],
                "link": raw["link"],
            }
            for key in (
                "name",
                "description",
                "type",
                "attribution",
                "attribution_link",
                "contact_email",
                "updatedAt",
                "createdAt",
                "metadata_updated_at",
                "data_updated_at",
                "columns_name",
                "columns_description",
                "provenance",
                "publication_date",
            ):
                record[key] = raw["resource"].get(key)
            # Todo: metadata
            yield record


def _stats(file):
    for line in file.open():
        if line.strip():
            doc = json.loads(line)
            doc.update(doc.pop("stats"))
            yield doc


if __name__ == "__main__":
    build_db()
