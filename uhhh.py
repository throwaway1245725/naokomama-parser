import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple

from patoolib import extract_archive

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-e", "--exclude", action="store_true")
args = arg_parser.parse_args()
exclude_mode: bool = args.exclude


patreon = Path.cwd() / "patreon"
rar_out = Path.cwd() / "rar_out"
rar_processed = Path.cwd() / "rar_processed"
out = Path.cwd() / "out"
exclusions_txt = out / "exclusions.txt"

FILENAME_PATTERN = re.compile(
    r"(?P<date>(?P<year>\d{4})-\d{2}-\d{2} \d{2}_\d{2}_\d{2})-(?P<id>\d+)-(?P<title>.*)-(?P<num1>\d+)(?: - (?P<num2>\d+))?$"
)

matches = {file: FILENAME_PATTERN.match(file.stem) for file in patreon.iterdir()}
rars = {f: m for f, m in matches.items() if f.suffix == ".rar"}
for rar, m in rars.items():
    dest_dir = rar_out / rar.stem
    if not dest_dir.exists():
        extract_archive(str(rar), outdir=str(rar_out / rar.stem))

for extracted_dir in rar_out.iterdir():
    files = sorted(extracted_dir.iterdir())
    num_digits = max(2, len(str(len(files))))
    for index, f in enumerate(files, start=1):
        dest_path = (
            rar_processed / f"{extracted_dir.stem} - {index:0{num_digits}}{f.suffix}"
        )
        shutil.copy(f, dest_path)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}

file_matches = {f: m for f, m in matches.items() if f.suffix in IMAGE_SUFFIXES}
additional_matches = {
    file: FILENAME_PATTERN.match(file.stem) for file in rar_processed.iterdir()
}
all_matches = {**file_matches, **additional_matches}

for file, m in all_matches.items():
    if not m:
        raise Exception("what")

with exclusions_txt.open("r") as f:
    exclusions: Set[Path] = {Path(line) for line in f.read().splitlines()}

years = {m["year"] for m in all_matches.values()}
year_matches = {
    year: {f: m for f, m in all_matches.items() if m["year"] == year} for year in years
}

year_filemoves: Dict[str, List[Tuple[Path, Path]]] = {}
for year, matches in year_matches.items():
    year_dir = out / year
    if not year_dir.exists():
        year_dir.mkdir()
    sorted_matches = sorted(
        matches.items(),
        key=lambda entry: (
            entry[1]["date"],
            -int(entry[1]["num1"]),
            -int(entry[1]["num2"]),
        )
        if entry[1]["num2"]
        else (entry[1]["date"], -int(entry[1]["num1"])),
        reverse=True,
    )
    year_filemoves[year] = [
        (file, year_dir / f"{file.name}") for file, _ in sorted_matches
    ]


if exclude_mode:
    actual_dest_paths = {
        path.with_name(re.sub(r"^\d+ - ", "", path.name))
        for year in years
        for path in (out / year).iterdir()
    }
    exclusions = {
        dest
        for filemoves in year_filemoves.values()
        for src, dest in filemoves
        if dest not in actual_dest_paths
    }
else:
    filtered_year_filemoves = {
        year: [(src, dest) for src, dest in filemoves if dest not in exclusions]
        for year, filemoves in year_filemoves.items()
    }

    for year, filemoves in filtered_year_filemoves.items():
        index_num_digits = max(2, len(str(len(filemoves))))
        for index, (src, dest) in enumerate(filemoves, start=1):
            actual_dest = dest.with_name(f"{index:0{index_num_digits}} - {dest.name}")
            if not actual_dest.exists():
                shutil.copy(src, actual_dest)


if exclude_mode:
    with exclusions_txt.open("w") as f:
        f.writelines(f"{str(exclusion)}\n" for exclusion in sorted(exclusions))
