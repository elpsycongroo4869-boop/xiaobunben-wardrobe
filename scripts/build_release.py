"""Build the bundled core and an upload-ready runtime ZIP."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "src/wardrobe2-core"
RUNTIME = REPO / "runtime"
VERSION = "5.0.2"


def files(directory):
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def checksums(directory, paths):
    return "".join(
        f"{sha256(path.read_bytes()).hexdigest()}  {path.relative_to(directory).as_posix()}\n"
        for path in paths
    ).encode("utf-8")


def add(zipped, name, data):
    zipped.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)


def main():
    entry = RUNTIME / "entry/current.json"
    pin = json.loads(entry.read_bytes())
    bundled_core = entry.parent / pin["archive"]["path"]
    bundled_core.parent.mkdir(exist_ok=True)
    core_files = files(CORE)
    with ZipFile(bundled_core, "w") as zipped:
        for path in core_files:
            add(zipped, f"{CORE.name}/{path.relative_to(CORE).as_posix()}", path.read_bytes())
        add(zipped, f"{CORE.name}/MANIFEST.sha256", checksums(CORE, core_files))
    pin["archive"]["sha256"] = sha256(bundled_core.read_bytes()).hexdigest()
    entry.write_bytes(json_bytes(pin))

    package_name = f"xiaobunben-wardrobe-2-v{VERSION}.zip"
    manifest = REPO / "release-manifest.json"
    manifest.write_bytes(json_bytes({
        "schema": "wardrobe2-public-release-v1",
        "version": VERSION,
        "launch_name": package_name,
        "runtime_entry": "runtime/entry/p14.py",
        "core_archive": bundled_core.relative_to(REPO).as_posix(),
        "core_sha256": pin["archive"]["sha256"],
        "curated_world_count": 200,
        "preset_point_count": 800,
        "candidate_count_default": 10,
    }))
    checksum = RUNTIME / "SHA256SUMS.txt"
    checksum.write_bytes(checksums(RUNTIME, [p for p in files(RUNTIME) if p != checksum]))
    package = REPO.parent / package_name
    with ZipFile(package, "w") as zipped:
        for path in [REPO / "CHATGPT.md", REPO / "LICENSE", manifest, *files(RUNTIME)]:
            add(zipped, f"{REPO.name}/{path.relative_to(REPO).as_posix()}", path.read_bytes())
    digest = sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".sha256").write_bytes(f"{digest}  {package.name}\n".encode("ascii"))
    print(f"{package.name} {digest}")


if __name__ == "__main__":
    main()
