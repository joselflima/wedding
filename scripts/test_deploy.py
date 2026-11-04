"""Check deployment failure boundaries without connecting to a real server."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SHA = "a" * 40


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.app = self.base / "app"
        self.app.mkdir()
        (self.app / ".git").mkdir()
        (self.app / ".env").touch()
        (self.app / "compose.production.yaml").touch()
        self.log = self.base / "commands"
        self.env = {
            **os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}",
            "TEST_LOG": str(self.log), "TEST_MAIN": SHA,
            "TEST_DIRTY": "", "TEST_DOCKER_FAIL": "", "TEST_SSH_FAIL": "0",
        }
        self.executable("flock", '#!/bin/bash\nexit 0\n')
        self.executable("git", '''#!/bin/bash
printf 'git %s\\n' "$*" >> "$TEST_LOG"
case "$1" in
  status) printf '%s' "$TEST_DIRTY" ;;
  rev-parse) printf '%s\\n' "$TEST_MAIN" ;;
esac
''')
        self.executable("docker", '''#!/bin/bash
printf 'docker %s\\n' "$*" >> "$TEST_LOG"
if [[ -n "$TEST_DOCKER_FAIL" && "$*" == *"$TEST_DOCKER_FAIL"* ]]; then exit 1; fi
''')

    def executable(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o700)

    def commands(self):
        return self.log.read_text() if self.log.exists() else ""

    def remote(self):
        return subprocess.run(["bash", str(ROOT / "scripts/deploy-vps.sh"), str(self.app), SHA],
                              env=self.env, text=True, capture_output=True)

    def test_unprepared_server_is_untouched(self):
        (self.app / "compose.production.yaml").unlink()
        self.assertNotEqual(self.remote().returncode, 0)
        self.assertEqual(self.commands(), "")

    def test_local_changes_are_not_overwritten(self):
        self.env["TEST_DIRTY"] = " M src/config/settings.py"
        self.assertNotEqual(self.remote().returncode, 0)
        self.assertNotIn("checkout", self.commands())
        self.assertNotIn("docker", self.commands())

    def test_superseded_commit_is_not_deployed(self):
        self.env["TEST_MAIN"] = "b" * 40
        self.assertEqual(self.remote().returncode, 0)
        self.assertNotIn("checkout", self.commands())
        self.assertNotIn("docker", self.commands())

    def test_failed_production_checks_prevent_migration(self):
        self.env["TEST_DOCKER_FAIL"] = "check --deploy"
        self.assertNotEqual(self.remote().returncode, 0)
        self.assertNotIn("migrate", self.commands())
        self.assertNotIn("--wait-timeout", self.commands())

    def test_failed_migration_prevents_service_replacement(self):
        self.env["TEST_DOCKER_FAIL"] = "migrate --noinput"
        self.assertNotEqual(self.remote().returncode, 0)
        self.assertNotIn("--wait-timeout", self.commands())

    def test_success_uses_exact_commit_and_preserves_volume(self):
        self.assertEqual(self.remote().returncode, 0)
        log = self.commands()
        self.assertIn(f"checkout --detach {SHA}", log)
        self.assertLess(log.index("check --deploy"), log.index("migrate --noinput"))
        self.assertLess(log.index("migrate --noinput"), log.index("--wait-timeout"))
        self.assertIn("--project-name wedding", log)
        self.assertNotIn("down", log)
        self.assertNotIn("--volumes", log)

    def transport_env(self):
        self.executable("ssh", '''#!/bin/bash
printf 'ssh %s\\n' "$*" >> "$TEST_LOG"
cat > /dev/null
exit "$TEST_SSH_FAIL"
''')
        return {**self.env, "VPS_HOST": "example.test", "VPS_USER": "deploy", "VPS_PORT": "22",
                "VPS_APP_DIR": "/srv/wedding", "VPS_SSH_KEY": "test-only-key",
                "VPS_KNOWN_HOSTS": "test-only-host", "DEPLOY_SHA": SHA, "RUNNER_TEMP": str(self.base)}

    def transport(self, env):
        return subprocess.run(["bash", str(ROOT / "scripts/run-deploy.sh")], env=env,
                              capture_output=True, text=True)

    def test_unsafe_remote_arguments_never_reach_ssh(self):
        for field, value in [("VPS_HOST", "host; echo bad"), ("VPS_USER", "-oProxyCommand=bad"),
                             ("VPS_APP_DIR", "/srv/app'; echo bad"), ("DEPLOY_SHA", "main"),
                             ("VPS_PORT", "65536"), ("VPS_PORT", "0")]:
            with self.subTest(field=field):
                env = self.transport_env()
                env[field] = value
                self.assertNotEqual(self.transport(env).returncode, 0)
                self.assertEqual(self.commands(), "")

    def test_host_verification_and_key_cleanup_even_on_failure(self):
        env = self.transport_env()
        env["TEST_SSH_FAIL"] = "7"
        result = self.transport(env)
        self.assertEqual(result.returncode, 7)
        self.assertIn("StrictHostKeyChecking=yes", self.commands())
        self.assertIn("BatchMode=yes", self.commands())
        self.assertEqual(list(self.base.glob("wedding-ssh.*")), [])
        self.assertNotIn("test-only-key", result.stdout + result.stderr + self.commands())


if __name__ == "__main__":
    unittest.main()
