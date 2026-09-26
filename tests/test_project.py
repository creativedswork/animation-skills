"""Synthetic records test tooling only; they are not animation evaluations."""

import copy
import importlib.util
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("project", REPO / "tools/project.py")
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for folder in (".trae/skills", "cases", "templates"):
            shutil.copytree(REPO / folder, self.root / folder, ignore=shutil.ignore_patterns("runs"))
        for filename in ("catalog.json", "assets.json"):
            shutil.copyfile(REPO / filename, self.root / filename)
        assets = project.load(self.root / "assets.json")
        for asset_id, asset in assets.items():
            path = self.root / asset["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("SYNTHETIC TEST INPUT " + asset_id).encode())
            asset["sha256"] = project.file_hash(path)
        project.write(self.root / "assets.json", assets)

    def ready_for_release(self):
        catalog = project.load(self.root / "catalog.json")
        catalog["version"] = "0.1.0"
        for skill in catalog["skills"]:
            skill["maturity"] = "validated"
        project.write(self.root / "catalog.json", catalog)
        for case in project.check(self.root)["cases"].values():
            path = project.new_run(case["id"], "test-only", self.root)
            run = project.load(path)
            run["status"] = "reviewed"
            run["environment"] = {key: "synthetic tooling test" for key in run["environment"]}
            run["execution"] = {
                "from_raw_inputs": True, "human_artifact_edits": False,
                "human_extra_guidance": False, "notes": "Synthetic fixture, not real production."}
            run["initial"] = self.accepted_version(case, "initial")
            project.write(path, run)

    def accepted_version(self, case, version):
        artifacts = []
        for filename in case["deliverables"]:
            relative = ".artifacts/runs/{}/{}/{}".format(case["id"], version, filename)
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("SYNTHETIC TOOLING TEST " + relative).encode())
            role = {".blend": "blend", ".glb": "export", ".mp4": "video"}[path.suffix]
            artifacts.append({"role": role, "path": relative, "sha256": project.file_hash(path)})
        return {"artifacts": artifacts, "review": {
            "verdict": "accepted", "reviewer": "synthetic test fixture",
            "correctness": {x["id"]: {"passed": True, "evidence": "Synthetic criterion test"}
                            for x in case["criteria"]["correctness"]},
            "taste": {x["id"]: {"score": 4, "evidence": "Synthetic score test"}
                      for x in case["criteria"]["taste"]},
            "remaining_issues": []}}

    def test_preview_is_standalone_and_reproducible(self):
        (self.root / "lessons").mkdir()
        (self.root / "lessons/DO-NOT-PUBLISH.txt").write_text("private answers")
        first = project.package(self.root)
        manifest = project.load(first / "manifest.json")
        self.assertEqual(manifest["channel"], "preview")
        first_hashes = {p.name: project.file_hash(p) for p in first.iterdir()}
        for entry in manifest["skills"]:
            self.assertEqual(entry["maturity"], "draft")
            with zipfile.ZipFile(first / entry["archive"]) as archive:
                expected = {entry["name"] + "/" + name for name in entry["files"]}
                self.assertEqual(set(archive.namelist()), expected)
                extracted = self.root / "unpacked" / entry["name"]
                archive.extractall(extracted)
                self.assertEqual(project.skill_manifest(extracted / entry["name"]), entry["files"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            project.package(self.root)
        shutil.rmtree(first)
        second = project.package(self.root)
        self.assertEqual(first_hashes, {p.name: project.file_hash(p) for p in second.iterdir()})

    def test_links_cannot_escape_or_disappear(self):
        folder = self.root / ".trae/skills/character-body-mechanics"
        path = folder / "SKILL.md"
        original = path.read_text()
        for link, message in [("../../outside.md", "Cross-package"), ("references/missing.md", "Missing packaged")]:
            with self.subTest(link=link):
                path.write_text(original + "\n[bad](" + link + ")\n")
                with self.assertRaisesRegex(ValueError, message):
                    project.check(self.root)
        path.write_text(original)
        (folder / "assets").mkdir()
        (folder / "assets/leak").symlink_to(self.root / "assets.json")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            project.check(self.root)

    def test_prepare_verifies_inputs_and_excludes_answers(self):
        assets = project.load(self.root / "assets.json")
        source = self.root / assets["survivor-rig-glb"]["path"]
        original = source.read_bytes()
        source.write_bytes(b"changed")
        destination = self.root / "work"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            project.prepare("walk-turn-stop", destination, self.root)
        self.assertFalse(destination.exists())
        source.write_bytes(original)
        project.prepare("walk-turn-stop", destination, self.root)
        self.assertEqual({p.relative_to(destination).as_posix()
                          for p in destination.rglob("*") if p.is_file()},
                         {"task.json", "inputs.json", "inputs/survivor-rig-glb.glb"})
        self.assertEqual(project.load(destination / "task.json")["id"], "walk-turn-stop")
        for record in project.load(destination / "inputs.json").values():
            project.verify_file(destination, record, "inputs")
        with self.assertRaisesRegex(ValueError, "already exists"):
            project.prepare("walk-turn-stop", destination, self.root)

    def test_new_run_is_pending_fingerprinted_and_not_overwritten(self):
        path = project.new_run("walk-turn-stop", "baseline-001", self.root, without_skills=True)
        run = project.load(path)
        self.assertEqual(run["status"], "recording")
        self.assertEqual(run["fingerprints"]["skills"], {})
        self.assertEqual(run["initial"]["artifacts"], [])
        self.assertEqual(run["initial"]["review"]["verdict"], "pending")
        with self.assertRaises(FileExistsError):
            project.new_run("walk-turn-stop", "baseline-001", self.root)
        case_path = self.root / "cases/walk-turn-stop/case.json"
        case = project.load(case_path)
        case["duration_seconds"] = 10
        project.write(case_path, case)
        with self.assertRaisesRegex(ValueError, "Case changed"):
            project.check(self.root)

    def test_formal_release_requires_actual_records_not_labels(self):
        with self.assertRaisesRegex(ValueError, "stable version"):
            project.check(self.root, release=True)
        catalog = project.load(self.root / "catalog.json")
        catalog["version"] = "0.1.0"
        project.write(self.root / "catalog.json", catalog)
        with self.assertRaisesRegex(ValueError, "draft Skills"):
            project.check(self.root, release=True)
        for skill in catalog["skills"]:
            skill["maturity"] = "validated"
        project.write(self.root / "catalog.json", catalog)
        with self.assertRaisesRegex(ValueError, "missing accepted evidence"):
            project.check(self.root, release=True)
        with self.assertRaisesRegex(ValueError, "prerelease version"):
            project.package(self.root)
        self.ready_for_release()
        output = project.package(self.root, release=True)
        self.assertEqual(project.load(output / "manifest.json")["channel"], "release")

    def test_release_rejects_false_success_records(self):
        self.ready_for_release()
        path = self.root / "cases/low-seat-transfer/runs/test-only.json"
        original = project.load(path)
        variants = []
        for field in ("human_artifact_edits", "human_extra_guidance"):
            value = copy.deepcopy(original)
            value["execution"][field] = True
            variants.append((field, value))
        value = copy.deepcopy(original)
        value["fingerprints"]["skills"]["character-body-mechanics"] = "0" * 64
        variants.append(("stale Skill", value))
        value = copy.deepcopy(original)
        value["fingerprints"]["skills"] = {}
        variants.append(("baseline", value))
        value = copy.deepcopy(original)
        value["initial"]["review"]["taste"]["adaptation"]["score"] = 3
        variants.append(("low taste", value))
        value = copy.deepcopy(original)
        value["initial"]["review"]["correctness"]["support"]["passed"] = False
        variants.append(("failed correctness", value))
        value = copy.deepcopy(original)
        value["environment"]["usage"] = None
        variants.append(("unknown usage", value))
        value = copy.deepcopy(original)
        value["initial"]["review"]["reviewer"] = " "
        variants.append(("no reviewer", value))
        value = copy.deepcopy(original)
        value["initial"]["review"]["verdict"] = "rejected"
        case = project.load(self.root / "cases/low-seat-transfer/case.json")
        value["corrected"] = self.accepted_version(case, "corrected")
        value["changes"] = [{"issue": "test issue", "change": "test change",
                             "actor": "fixture", "rationale": "synthetic"}]
        variants.append(("only correction accepted", value))
        for label, value in variants:
            with self.subTest(label=label):
                project.write(path, value)
                with self.assertRaises(ValueError):
                    project.check(self.root, release=True)
        project.write(path, original)
        artifact = self.root / original["initial"]["artifacts"][0]["path"]
        artifact.write_bytes(b"initial evidence overwritten")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            project.check(self.root, release=True)

    def test_promoted_lesson_requires_transfer_for_its_skill_revision(self):
        self.ready_for_release()
        state = project.check(self.root)
        lesson = {
            "id": "test-only", "status": "promoted", "skill": "character-body-mechanics",
            "source": {"case": "sit-stand", "run": "test-only"},
            "observation": "Synthetic fixture", "effective_change": "Synthetic change",
            "applies_when": "Tooling tests only", "limits": "Not animation evidence",
            "targets": [".trae/skills/character-body-mechanics/references/sit-stand.md"],
            "validated_skill_sha256": state["hashes"]["character-body-mechanics"],
            "transfer_evidence": [{"case": "low-seat-transfer", "run": "test-only"}]}
        path = self.root / "lessons/test-only.json"
        path.parent.mkdir()
        project.write(path, lesson)
        project.check(self.root, release=True)
        lesson["transfer_evidence"] = []
        project.write(path, lesson)
        with self.assertRaisesRegex(ValueError, "needs transfer evidence"):
            project.check(self.root)
        lesson["transfer_evidence"] = [{"case": "low-seat-transfer", "run": "test-only"}]
        lesson["validated_skill_sha256"] = "0" * 64
        project.write(path, lesson)
        with self.assertRaisesRegex(ValueError, "different Skill revision"):
            project.check(self.root)


if __name__ == "__main__":
    unittest.main()
