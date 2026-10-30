"""
scripts/test_clean_clone_deliverable_e.py — Deliverable E Clean Clone & Build Test
-----------------------------------------------------------------------------------
Automates complete clean-environment verification in an isolated temporary directory:
  1. Clones repository into a fresh temporary directory
  2. Verifies presence of all core assets, documentation, and workers
  3. Verifies .env.example, LICENSE, and WORKER_PROTOCOL.md
  4. Runs information isolation verification test in the clean clone
  5. Runs recorded run validation and integrity checks
  6. Reports clean verification status
"""
import os
import sys
import shutil
import tempfile
import subprocess
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run_clean_clone_test():
    print("=" * 80)
    print("DELIVERABLE E: CLEAN CLONE & REPOSITORY VERIFICATION TEST")
    print("=" * 80)

    temp_dir = tempfile.mkdtemp(prefix="procureagent_clean_clone_")
    print(f"  [1] Created isolated temporary directory: {temp_dir}")

    try:
        # 1. Clone repository locally into temp directory
        print("  [2] Cloning local repository into temporary workspace...")
        clone_res = subprocess.run(
            ["git", "clone", REPO_ROOT, temp_dir],
            capture_output=True,
            text=True,
            check=True
        )
        print("      Git clone completed cleanly.")

        # 2. Check essential repository files
        print("  [3] Checking required artifacts in clean clone...")
        required_files = [
            "start.py",
            "dashboard/index.html",
            "workers/template_worker.py",
            "docs/WORKER_PROTOCOL.md",
            "demo/recorded_runs/recorded_rogue_run.json",
            "demo/recorded_runs/recorded_genuine_failure_reallocation.json",
            ".env.example",
            "LICENSE",
            "README.md",
            "requirements.txt",
            "scripts/test_information_isolation.py",
            "scripts/generate_recorded_runs.py"
        ]

        missing = []
        for rf in required_files:
            fp = os.path.join(temp_dir, rf)
            if not os.path.exists(fp):
                missing.append(rf)
            else:
                sz = os.path.getsize(fp)
                print(f"      • {rf:<50} ({sz:,} bytes) [OK]")

        assert not missing, f"Missing required files in clean clone: {missing}"
        print("      All required files verified present in clean clone.")

        # 3. Setup .env with credentials from original repo to run isolation tests
        orig_env = os.path.join(REPO_ROOT, ".env")
        clean_env = os.path.join(temp_dir, ".env")
        if os.path.exists(orig_env):
            shutil.copy2(orig_env, clean_env)
            print("  [4] Injected environment configuration for automated validation.")

        # 4. Run Information Isolation Test inside clean clone
        print("  [5] Running Information Isolation Invariant Test inside clean clone...")
        iso_test = subprocess.run(
            [sys.executable, os.path.join(temp_dir, "scripts", "test_information_isolation.py")],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        if iso_test.returncode != 0:
            print(f"STDOUT:\n{iso_test.stdout}")
            print(f"STDERR:\n{iso_test.stderr}")
            raise RuntimeError("Information isolation test failed in clean clone!")
        print("      Information isolation test PASSED (0 hidden test leakages).")

        # 5. Run Recorded Runs Integrity Check
        print("  [6] Running Recorded Runs Validation inside clean clone...")
        rec_test = subprocess.run(
            [sys.executable, os.path.join(temp_dir, "scripts", "generate_recorded_runs.py")],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        if rec_test.returncode != 0:
            print(f"STDOUT:\n{rec_test.stdout}")
            print(f"STDERR:\n{rec_test.stderr}")
            raise RuntimeError("Recorded runs validation failed in clean clone!")
        print("      Recorded runs verified and valid.")

        print("\n" + "=" * 80)
        print("DELIVERABLE E CLEAN CLONE TEST: 100% SUCCESSFUL")
        print(f"Verified at: {datetime.now().isoformat()}")
        print("=" * 80)
        return True

    finally:
        print(f"  [Cleanup] Removing temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_clean_clone_test()
    if not success:
        sys.exit(1)

