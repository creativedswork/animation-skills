#!/usr/bin/env python3
"""Local case records and standalone Skill packages; no production scheduling."""

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA = re.compile(r"[0-9a-f]{64}")
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[a-z0-9]+(?:[.-][a-z0-9]+)*)?")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def local_path(root, value, prefix=None):
    require(text(value), "Missing local path")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path: " + value)
    if prefix:
        require(relative.parts[:len(Path(prefix).parts)] == Path(prefix).parts,
                "Path must be under " + prefix + ": " + value)
    target = root / relative
    for part in (target,) + tuple(target.parents):
        if part == root:
            break
        require(not part.is_symlink(), "Symlink is not a package/evidence file: " + str(part))
    require(root.resolve() in target.resolve().parents, "Path escapes root: " + value)
    return target


def verify_file(root, record, prefix):
    path = local_path(root, record["path"], prefix)
    require(path.is_file(), "Missing artifact: " + str(path))
    require(file_hash(path) == record["sha256"], "SHA-256 mismatch: " + str(path))


def package_files(folder):
    require(folder.is_dir() and not folder.is_symlink(), "Missing Skill: " + str(folder))
    files = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        require(not path.is_symlink(), "Symlink in Skill: " + str(path))
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_file():
            require(relative.as_posix() == "SKILL.md" or
                    relative.parts[0] in {"references", "scripts", "assets"},
                    "Unexpected package resource: " + str(path))
            require(path.suffix != ".pyc", "Compiled file in Skill: " + str(path))
            files.append(path)
    require(folder / "SKILL.md" in files, "Missing SKILL.md: " + str(folder))
    return files


def skill_manifest(folder):
    files = package_files(folder)
    body = (folder / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n\n# ", body)
    require(match is not None, "Expected portable name/description frontmatter: " + str(folder))
    require(match[1] == folder.name, "Skill name does not match directory: " + str(folder))
    require("Use " in match[2] and not any(x in match[2] for x in (": ", "<", ">", '"', "'")),
            "Description must state activation in a plain scalar: " + str(folder))
    for path in files:
        if path.suffix != ".md":
            continue
        for link in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)", path.read_text(encoding="utf-8")):
            parsed = urlsplit(link)
            if parsed.scheme in {"https", "http", "mailto"} or link.startswith("#"):
                continue
            require(not parsed.scheme and not parsed.netloc, "Unsupported resource link: " + link)
            target = path.parent / unquote(parsed.path)
            require(folder.resolve() in target.resolve().parents,
                    "Cross-package link: " + str(path) + " -> " + link)
            require(target.resolve() in {p.resolve() for p in files},
                    "Missing packaged resource: " + str(path) + " -> " + link)
    return {p.relative_to(folder).as_posix(): file_hash(p) for p in files}


def check_case(case, folder, skills, assets):
    require(case["id"] == folder.name and NAME.fullmatch(case["id"]), "Case ID mismatch")
    require(case["skill"] in skills, "Unknown case Skill: " + case["skill"])
    require(case["split"] in {"development", "transfer"}, "Invalid case split")
    for field in ("title", "prompt"):
        require(text(case[field]), "Missing case " + field)
    require(isinstance(case["inputs"], list) and case["inputs"] and
            len(case["inputs"]) == len(set(case["inputs"])) and
            all(x in assets for x in case["inputs"]), "Unknown or duplicate case inputs")
    for field in ("scene", "camera"):
        require(isinstance(case[field], dict) and case[field], "Missing case " + field)
    require(type(case["fps"]) is int and case["fps"] > 0, "Invalid fps")
    require(type(case["duration_seconds"]) in (int, float) and case["duration_seconds"] > 0,
            "Invalid duration")
    require(isinstance(case["deliverables"], list) and case["deliverables"] and
            all(text(x) and Path(x).name == x for x in case["deliverables"]), "Invalid deliverables")
    require(type(case["minimum_taste"]) is int and 1 <= case["minimum_taste"] <= 5,
            "Invalid minimum taste")
    require(type(case["required_for_release"]) is bool, "Missing release coverage decision")
    ids = []
    for group in ("correctness", "taste"):
        require(isinstance(case["criteria"][group], list) and case["criteria"][group],
                "Missing criteria: " + group)
        for criterion in case["criteria"][group]:
            require(NAME.fullmatch(criterion["id"]) and text(criterion["description"]),
                    "Invalid criterion")
            ids.append(criterion["id"])
    require(len(ids) == len(set(ids)), "Duplicate criterion ID")


def check_version(version, case, root, artifacts):
    review = version["review"]
    require(review["verdict"] in {"pending", "accepted", "rejected"}, "Invalid review verdict")
    require(isinstance(review["remaining_issues"], list), "Missing remaining issues")
    require(isinstance(version["artifacts"], list), "Invalid artifacts")
    paths, roles = [], set()
    for artifact in version["artifacts"]:
        path = local_path(root, artifact["path"], ".artifacts")
        require(SHA.fullmatch(artifact["sha256"]), "Invalid artifact SHA-256")
        require(artifact["role"] in {"blend", "export", "video", "other"}, "Invalid artifact role")
        if artifact["role"] == "blend":
            require(path.suffix == ".blend", "Blend evidence must be a .blend file")
        paths.append(artifact["path"])
        roles.add(artifact["role"])
        if artifacts:
            verify_file(root, artifact, ".artifacts")
    require(len(paths) == len(set(paths)), "Duplicate artifact path")
    if review["verdict"] == "pending":
        return paths
    require(text(review["reviewer"]), "Reviewed work needs an identified reviewer")
    require({"blend", "export", "video"} <= roles, "Reviewed work needs blend, export and video")
    for group in ("correctness", "taste"):
        expected = {x["id"] for x in case["criteria"][group]}
        require(set(review[group]) == expected, "Review must cover every " + group + " criterion")
        for value in review[group].values():
            require(text(value["evidence"]), "Missing review evidence")
            if group == "correctness":
                require(type(value["passed"]) is bool, "Correctness requires a boolean")
            else:
                require(type(value["score"]) is int and 1 <= value["score"] <= 5,
                        "Taste requires a score from 1 to 5")
    if review["verdict"] == "accepted":
        require(all(x["passed"] for x in review["correctness"].values()),
                "Accepted work has failed correctness criteria")
        require(all(x["score"] >= case["minimum_taste"] for x in review["taste"].values()),
                "Accepted work is below minimum taste")
        require(set(case["deliverables"]) <= {Path(x).name for x in paths},
                "Accepted work is missing case deliverables")
    return paths


def check_run(run, path, case, skills, assets, root, artifacts):
    require(run["id"] == path.stem and NAME.fullmatch(run["id"]), "Run ID mismatch")
    require(run["case"] == case["id"], "Run case mismatch")
    require(run["status"] in {"recording", "reviewed"}, "Invalid run status")
    fp = run["fingerprints"]
    require(fp["case"] == content_hash(case), "Case changed after run creation; create a new case ID")
    require(fp["inputs"] == {x: assets[x]["sha256"] for x in case["inputs"]},
            "Run input fingerprints do not match fixed inputs")
    require(isinstance(fp["skills"], dict) and set(fp["skills"]) <= set(skills) and
            all(isinstance(x, str) and SHA.fullmatch(x) for x in fp["skills"].values()),
            "Invalid run Skill fingerprints")
    initial_paths = check_version(run["initial"], case, root, artifacts)
    if run["corrected"] is not None:
        corrected_paths = check_version(run["corrected"], case, root, artifacts)
        require(not set(initial_paths) & set(corrected_paths), "Correction overwrites initial artifacts")
        require(run["changes"], "Corrected work requires a change record")
    for change in run["changes"]:
        require(all(text(change[x]) for x in ("issue", "change", "actor", "rationale")),
                "Incomplete change record")
    require(isinstance(run["lessons"], list), "Invalid lesson links")
    if run["status"] == "reviewed":
        require(all(text(run["environment"][x]) for x in ("model", "harness", "blender", "budget", "usage")),
                "Reviewed run needs model, harness, Blender, budget and actual usage")
        require(all(type(run["execution"][x]) is bool for x in
                    ("from_raw_inputs", "human_artifact_edits", "human_extra_guidance")),
                "Reviewed run must disclose input origin and human assistance")
        require(text(run["execution"]["notes"]), "Execution notes must describe assistance or its absence")
        for version in (run["initial"], run["corrected"]):
            require(version is None or version["review"]["verdict"] != "pending",
                    "Reviewed run contains pending work")


def accepted(run):
    return run["status"] == "reviewed" and any(
        version is not None and version["review"]["verdict"] == "accepted"
        for version in (run["initial"], run["corrected"]))


def independent_initial(run):
    execution = run["execution"]
    return (run["status"] == "reviewed" and run["initial"]["review"]["verdict"] == "accepted"
            and execution["from_raw_inputs"] is True
            and execution["human_artifact_edits"] is False
            and execution["human_extra_guidance"] is False)


def check(root=ROOT, artifacts=False, release=False):
    catalog, assets = load(root / "catalog.json"), load(root / "assets.json")
    require(VERSION.fullmatch(catalog["version"]), "Invalid project version")
    skills = {}
    for entry in catalog["skills"]:
        name = entry["name"]
        require(NAME.fullmatch(name) and 2 <= len(name) <= 64 and name not in skills, "Invalid Skill name")
        require(entry["maturity"] in {"draft", "validated"}, "Invalid maturity")
        folder = root / ".trae" / "skills" / name
        skills[name] = {"entry": entry, "files": skill_manifest(folder)}
    require(skills, "No Skills in catalog")
    require(set(skills) == {p.name for p in (root / ".trae/skills").iterdir() if p.is_dir()},
            "Catalog and Skill directories differ")
    hashes = {name: content_hash(value["files"]) for name, value in skills.items()}
    require(isinstance(assets, dict) and assets, "No asset manifest")
    for asset_id, asset in assets.items():
        require(NAME.fullmatch(asset_id) and text(asset["source"]), "Invalid asset provenance")
        local_path(root, asset["path"], ".artifacts/inputs")
        require(SHA.fullmatch(asset["sha256"]), "Invalid input SHA-256")
        if artifacts or release:
            verify_file(root, asset, ".artifacts/inputs")
    cases, runs = {}, {}
    for path in sorted((root / "cases").glob("*/case.json")):
        case = load(path)
        check_case(case, path.parent, skills, assets)
        cases[case["id"]] = case
        for run_path in sorted((path.parent / "runs").glob("*.json")):
            run = load(run_path)
            check_run(run, run_path, case, skills, assets, root, artifacts or release)
            runs[(case["id"], run["id"])] = run
    require(cases, "No production cases")
    lessons = {}

    def evidence(reference):
        key = (reference["case"], reference["run"])
        require(key in runs, "Unknown evidence run: " + repr(key))
        return runs[key]

    for path in sorted((root / "lessons").glob("*.json")):
        lesson = load(path)
        require(lesson["id"] == path.stem and NAME.fullmatch(lesson["id"]), "Lesson ID mismatch")
        require(lesson["status"] in {"candidate", "promoted"} and lesson["skill"] in skills,
                "Invalid lesson status or Skill")
        require(all(text(lesson[x]) for x in ("observation", "effective_change", "applies_when", "limits")),
                "Lesson needs an observation, effective change, conditions and limits")
        source = evidence(lesson["source"])
        require(lesson["targets"], "Lesson needs target Skill files")
        prefix = ".trae/skills/" + lesson["skill"]
        for target in lesson["targets"]:
            require(local_path(root, target, prefix).is_file(), "Missing lesson target: " + target)
        if lesson["status"] == "promoted":
            require(accepted(source) and lesson["skill"] in source["fingerprints"]["skills"],
                    "Promoted lesson needs accepted source work with the Skill")
            require(lesson["transfer_evidence"], "Promoted lesson needs transfer evidence")
            require(isinstance(lesson["validated_skill_sha256"], str) and
                    SHA.fullmatch(lesson["validated_skill_sha256"]), "Missing validated Skill fingerprint")
        for reference in lesson["transfer_evidence"]:
            transfer = evidence(reference)
            require(cases[reference["case"]]["split"] == "transfer", "Lesson evidence must be transfer")
            if lesson["status"] == "promoted":
                require(independent_initial(transfer), "Promoted lesson needs an independent accepted initial")
                require(transfer["fingerprints"]["skills"].get(lesson["skill"]) ==
                        lesson["validated_skill_sha256"], "Lesson transfer used a different Skill revision")
        lessons[lesson["id"]] = lesson
    for run in runs.values():
        require(set(run["lessons"]) <= set(lessons), "Run links to an unknown lesson")
    if release:
        require("-" not in catalog["version"], "Formal release requires a stable version")
        require(all(x["entry"]["maturity"] == "validated" for x in skills.values()),
                "Formal release blocked: draft Skills have no validated capability claim")
        for name in skills:
            required = [c for c in cases.values() if c["skill"] == name and c["required_for_release"]]
            require({c["split"] for c in required} == {"development", "transfer"},
                    "Release needs development and transfer coverage for " + name)
            for case in required:
                candidates = [r for (case_id, _), r in runs.items() if case_id == case["id"]]
                if case["split"] == "development":
                    passed = any(accepted(r) and name in r["fingerprints"]["skills"] for r in candidates)
                else:
                    passed = any(independent_initial(r) and r["fingerprints"]["skills"] == hashes
                                 for r in candidates)
                require(passed, "Release missing accepted evidence: " + case["id"])
    return {"catalog": catalog, "assets": assets, "skills": skills, "hashes": hashes,
            "cases": cases, "runs": runs, "lessons": lessons}


def prepare(case_id, destination, root=ROOT):
    state = check(root)
    require(case_id in state["cases"], "Unknown case: " + case_id)
    case = state["cases"][case_id]
    destination = Path(destination).resolve()
    require(not destination.exists(), "Destination already exists: " + str(destination))
    for asset_id in case["inputs"]:
        verify_file(root, state["assets"][asset_id], ".artifacts/inputs")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        stage = Path(temporary) / "prepared"
        (stage / "inputs").mkdir(parents=True)
        inputs = {}
        for asset_id in case["inputs"]:
            asset = state["assets"][asset_id]
            relative = "inputs/" + asset_id + Path(asset["path"]).suffix
            shutil.copyfile(root / asset["path"], stage / relative)
            require(file_hash(stage / relative) == asset["sha256"], "Input changed while preparing")
            inputs[asset_id] = {"path": relative, "sha256": asset["sha256"]}
        write(stage / "task.json", case)
        write(stage / "inputs.json", inputs)
        stage.rename(destination)
    return destination


def new_run(case_id, run_id, root=ROOT, without_skills=False):
    state = check(root, artifacts=True)
    require(case_id in state["cases"], "Unknown case: " + case_id)
    require(NAME.fullmatch(run_id), "Run ID must be kebab-case")
    case = state["cases"][case_id]
    run = load(root / "templates/run.json")
    run.update(id=run_id, case=case_id, fingerprints={
        "case": content_hash(case),
        "skills": {} if without_skills else state["hashes"],
        "inputs": {x: state["assets"][x]["sha256"] for x in case["inputs"]}})
    path = root / "cases" / case_id / "runs" / (run_id + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(run, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return path


def package(root=ROOT, release=False):
    state = check(root, release=release)
    version = state["catalog"]["version"]
    require(release or "-" in version, "Preview packages require a prerelease version suffix")
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    destination = dist / version
    require(not destination.exists(), "Package version already exists: " + str(destination))
    manifest = {"version": version, "channel": "release" if release else "preview", "skills": []}
    with tempfile.TemporaryDirectory(dir=dist) as temporary:
        stage = Path(temporary) / "package"
        stage.mkdir()
        for name, skill in sorted(state["skills"].items()):
            archive = name + "-" + version + ".zip"
            folder = root / ".trae/skills" / name
            with zipfile.ZipFile(stage / archive, "w") as output:
                for relative, expected in sorted(skill["files"].items()):
                    data = (folder / relative).read_bytes()
                    require(hashlib.sha256(data).hexdigest() == expected, "Skill changed while packaging")
                    info = zipfile.ZipInfo(name + "/" + relative, (1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    output.writestr(info, data)
            manifest["skills"].append(dict(skill["entry"], archive=archive,
                                           sha256=file_hash(stage / archive),
                                           source_sha256=state["hashes"][name], files=skill["files"]))
        write(stage / "manifest.json", manifest)
        sums = "".join(file_hash(path) + "  " + path.name + "\n" for path in sorted(stage.iterdir()))
        (stage / "SHA256SUMS").write_text(sums, encoding="utf-8")
        stage.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("check", help="Check structure and evidence records, not animation quality")
    validate.add_argument("--artifacts", action="store_true", help="Verify local artifact bytes")
    validate.add_argument("--release", action="store_true", help="Require stable version and release evidence")
    prep = commands.add_parser("prepare", help="Copy one task and its verified inputs into a new directory")
    prep.add_argument("case")
    prep.add_argument("destination", type=Path)
    record = commands.add_parser("new-run", help="Create a pending record; does not run a production task")
    record.add_argument("case")
    record.add_argument("run_id")
    record.add_argument("--without-skills", action="store_true", help="Record a no-Skill baseline")
    pack = commands.add_parser("package", help="Build standalone ZIPs, manifest and SHA256SUMS")
    pack.add_argument("--release", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "check":
            state = check(artifacts=args.artifacts, release=args.release)
            print("OK: {} Skills, {} cases, {} runs, {} lessons; animation quality not evaluated".format(
                len(state["skills"]), len(state["cases"]), len(state["runs"]), len(state["lessons"])))
        elif args.command == "prepare":
            print(prepare(args.case, args.destination))
        elif args.command == "new-run":
            print(new_run(args.case, args.run_id, without_skills=args.without_skills))
        else:
            print(package(release=args.release))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
