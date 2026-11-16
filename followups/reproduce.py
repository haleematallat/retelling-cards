"""Reproduce both released follow-ups and check the demo's displayed totals."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from html.parser import HTMLParser


class DemoArchive(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.in_archive = False
        self.archive_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "archive":
            self.archive_count += 1
            self.in_archive = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_archive = False

    def handle_data(self, data):
        if self.in_archive:
            self.parts.append(data)

    def results(self):
        if self.archive_count != 1:
            raise ValueError("Expected one data archive in the demo")
        return json.loads("".join(self.parts))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def reproduce(root, temporary, folder, script, published_filename, extra=()):
    directory = root / folder
    recomputed = temporary / published_filename
    subprocess.run(
        [sys.executable, str(directory / script), *extra, "--out", str(recomputed)],
        check=True,
    )
    results = load_json(recomputed)
    if results != load_json(directory / published_filename):
        raise ValueError(f"Published results differ from the reproduced {folder} analysis")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="retelling-followups-") as location:
        temporary = Path(location)
        mechanism = reproduce(
            root, temporary, "reader-experiment", "mechanism.py",
            "mechanism-results.json", ["--independent"],
        )
        closed_book = reproduce(
            root, temporary, "closed-book", "summarize.py", "followup-results.json",
        )
    archive = DemoArchive()
    archive.feed((root.parent / "docs" / "followup.html").read_text(encoding="utf-8"))
    data = archive.results()
    if data["summary"] != closed_book:
        raise ValueError("The demo's closed-book results differ from the released analysis")
    if data["recovery"]["result"] != mechanism["slices"]["independent_consensus_on_card"]["summary"]:
        raise ValueError("The demo's recovery results differ from the released analysis")
    if data["recovery"]["offCard"] != mechanism["slices"]["consensus_off_card"]["summary"]:
        raise ValueError("The demo's off-card results differ from the released analysis")
    if data["recovery"]["checks"] != mechanism["outcome_checks_independent"]:
        raise ValueError("The demo's blind judgment count differs from the released analysis")
    print("Reproduced both follow-ups and verified the figures shown in the demo.")


if __name__ == "__main__":
    main()
