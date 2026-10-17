"""Run with python3 tests/pr_regressions.py; requires PHP CLI with Fileinfo.

All requests use a temporary application copy and disposable files on loopback.
"""

import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PRRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = shutil.which("php")
        if not cls.php:
            raise RuntimeError("PHP CLI is required")
        cls.temp = tempfile.TemporaryDirectory(prefix="tinyfm-regression-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        source = Path(__file__).resolve().parents[1]
        for name in ("tinyfilemanager.php", "translation.json"):
            shutil.copy2(source / name, cls.root / name)
        (cls.root / "data").mkdir()
        (cls.root / "sessions").mkdir()
        cls.password = secrets.token_hex(16)
        password_hash = subprocess.check_output(
            [cls.php, "-r", "echo password_hash($argv[1], PASSWORD_DEFAULT);", cls.password],
            text=True,
        )
        (cls.root / "config.php").write_text(
            "<?php\n// Test configuration\n"
            "$CONFIG = '{\"lang\":\"en\",\"error_reporting\":false,\"show_hidden\":false}';\n"
            "$root_path = __DIR__ . '/data';\n"
            "$auth_users = array('qa' => '" + password_hash + "');\n"
            "$readonly_users = array();\n"
            "$global_readonly = false;\n"
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.url = f"http://127.0.0.1:{port}/tinyfilemanager.php"
        cls.log = open(cls.root / "server.log", "w+")
        cls.addClassCleanup(cls.log.close)
        cls.server = subprocess.Popen(
            [cls.php, "-d", "session.save_handler=files",
             "-d", f"session.save_path={cls.root / 'sessions'}",
             "-d", "opcache.enable=0", "-S", f"127.0.0.1:{port}"],
            cwd=cls.root, stdout=cls.log, stderr=cls.log,
            env={k: v for k, v in os.environ.items() if k != "PHP_CLI_SERVER_WORKERS"},
        )
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            if cls.server.poll() is not None:
                cls.log.seek(0)
                raise RuntimeError(cls.log.read())
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("PHP server did not become ready")

    @classmethod
    def stop_server(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait()

    def setUp(self):
        self.jar = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect(),
        )
        self.file = self.root / "data" / "edit.txt"
        self.file.write_text("original")

    def request(self, query="?p=", data=None, json_body=False, cookie=None, content_type=None):
        headers = {"Content-Type": content_type} if content_type else {}
        if data is not None:
            if json_body:
                data = json.dumps(data).encode()
                headers["Content-Type"] = "application/json; charset=utf-8"
            elif not isinstance(data, bytes):
                data = urllib.parse.urlencode(data).encode()
        if cookie is not None:
            headers["Cookie"] = "filemanager=" + cookie
        req = urllib.request.Request(self.url + query, data=data, headers=headers)
        try:
            response = self.client.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode()

    def upload(self, token, filename, fullpath=None, content=b"uploaded", chunk=None, upload_id=None):
        boundary = "tinyfm-" + secrets.token_hex(12)
        fields = {"token": token, "fullpath": fullpath if fullpath is not None else filename,
                  "dzchunkindex": "0", "dztotalchunkcount": "0"}
        if chunk is not None:
            fields.update(dzchunkindex=str(chunk[0]), dztotalchunkcount=str(chunk[1]))
            fields["dzuuid"] = upload_id or hashlib.sha256(
                (fullpath or filename).encode()).hexdigest()
        body = b""
        for key, value in fields.items():
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
                     f'{value}\r\n').encode()
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                 f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        body += content + f"\r\n--{boundary}--\r\n".encode()
        return self.request(data=body, content_type=f"multipart/form-data; boundary={boundary}")

    def session_id(self):
        return next(c.value for c in self.jar if c.name == "filemanager")

    def login(self):
        status, _, body = self.request()
        self.assertEqual(status, 200)
        match = re.search(r'name="token" value="([^"]+)"', body)
        self.assertIsNotNone(match, "Expected a login form with a CSRF token")
        token = match.group(1)
        old_id = self.session_id()
        status, _, _ = self.request(data={
            "fm_usr": "qa", "fm_pwd": self.password, "token": token,
        })
        self.assertEqual(status, 302)
        self.login_token = token
        status, _, body = self.request()
        self.assertEqual(status, 200)
        match = re.search(r"window.csrf = '([^']+)'", body)
        self.assertIsNotNone(match, "Expected an authenticated page")
        return match.group(1), old_id

    def save(self, token, content="saved"):
        return self.request("?p=&edit=edit.txt", {
            "ajax": True, "type": "save", "token": token, "content": content,
        }, json_body=True)

    def test_login_rotates_id_and_old_session_cannot_save(self):
        token, old_id = self.login()
        self.assertNotEqual(self.session_id(), old_id)
        self.assertNotEqual(token, self.login_token)
        status, _, _ = self.save(self.login_token, "known pre-login token")
        self.assertEqual(status, 409)
        self.assertEqual(self.file.read_text(), "original")
        status, _, _ = self.request("?p=&edit=edit.txt", {
            "ajax": True, "type": "save", "token": token, "content": "replayed",
        }, json_body=True, cookie=old_id)
        self.assertEqual(status, 401)
        self.assertEqual(self.file.read_text(), "original")

    def test_failed_login_does_not_authenticate(self):
        _, _, body = self.request()
        token = re.search(r'name="token" value="([^"]+)"', body).group(1)
        old_id = self.session_id()
        self.request(data={"fm_usr": "qa", "fm_pwd": "incorrect", "token": token})
        self.assertEqual(self.session_id(), old_id)
        status, _, _ = self.save(token)
        self.assertEqual(status, 401)
        self.assertEqual(self.file.read_text(), "original")

    def test_save_success_stale_token_and_expired_session(self):
        token, _ = self.login()
        status, headers, body = self.save(token)
        self.assertEqual((status, headers.get("X-TFM-Save-Success"), body), (200, "1", "1"))
        self.assertEqual(self.file.read_text(), "saved")
        status, headers, _ = self.save("invalid", "must not write")
        self.assertEqual(status, 409)
        self.assertEqual(headers.get("X-CSRF-Token"), token)
        self.assertEqual(self.file.read_text(), "saved")
        self.request("?logout=1")
        status, _, _ = self.save(token, "expired")
        self.assertEqual(status, 401)
        self.assertEqual(self.file.read_text(), "saved")

    def test_readonly_save_does_not_write_or_confirm_success(self):
        config = self.root / "config.php"
        original = config.read_text()
        try:
            config.write_text(original + "$readonly_users = array('qa');\n")
            token, _ = self.login()
            status, headers, body = self.save(token)
            self.assertEqual(status, 200)
            self.assertIsNone(headers.get("X-TFM-Save-Success"))
            self.assertNotEqual(body.strip(), "1")
            self.assertEqual(self.file.read_text(), "original")
        finally:
            config.write_text(original)

    def test_save_with_authentication_disabled(self):
        config = self.root / "config.php"
        original = config.read_text()
        try:
            config.write_text(original + "$use_auth = false;\n")
            status, _, body = self.request()
            self.assertEqual(status, 200)
            token = re.search(r"window.csrf = '([^']+)'", body).group(1)
            status, headers, body = self.save(token)
            self.assertEqual((status, headers.get("X-TFM-Save-Success"), body), (200, "1", "1"))
            self.assertEqual(self.file.read_text(), "saved")
        finally:
            config.write_text(original)

    def test_form_encoded_search_containing_save_is_preserved(self):
        token, _ = self.login()
        (self.root / "data" / "save-me.txt").write_text("search fixture")
        status, _, body = self.request(data={
            "ajax": True, "type": "search", "token": token,
            "path": ".", "content": "save",
        })
        self.assertEqual(status, 200)
        self.assertIn("save-me.txt", body)
        json.loads(body)
        status, _, body = self.request(data={
            "ajax": True, "type": "search", "token": "invalid",
            "path": ".", "content": "save",
        })
        self.assertEqual((status, body), (401, "Invalid Token."))

    def test_empty_extensionless_file_can_be_edited(self):
        self.login()
        (self.root / "data" / "empty").touch()
        status, _, body = self.request("?p=&edit=empty")
        self.assertEqual(status, 200)
        self.assertIn('id="normal-editor"', body)

    def test_download_preserves_plus_spaces_and_percent_names(self):
        token, _ = self.login()
        for name in ("literal+plus.txt", "with space.txt", "literal%2B.txt"):
            with self.subTest(name=name):
                (self.root / "data" / name).write_text(name)
                status, _, body = self.request(
                    "?p=&" + urllib.parse.urlencode({"dl": name}), {"token": token})
                self.assertEqual((status, body), (200, name))

    def test_settings_preserve_sample_comments_and_deployment_values(self):
        config = self.root / "config.php"
        original = config.read_text()
        base = "\n".join(line for line in original.splitlines()
                         if not line.startswith("$CONFIG ="))
        settings = {"ajax": "true", "type": "settings", "js-language": "en",
                    "js-error-report": "false", "js-show-hidden": "false",
                    "js-hide-cols": "false", "js-theme-3": "dark"}
        marker = "/* Keep deployment comment intact */\n$deployment = 'keep $1 \\\\ literal';\n"
        initial = ('{"lang":"en","error_reporting":false,"show_hidden":false,'
                   '"hide_Cols":false,"theme":"light"}')
        for assignment, newline in (
                ("", "\n"),
                (f"$CONFIG = '{initial}';\n", "\n"),
                (f"$CONFIG =\n'{initial}';\n", "\r\n")):
            with self.subTest(assignment=assignment, newline=repr(newline)):
                fixture = base.replace("<?php\n", "<?php\n" + marker + assignment, 1)
                config.write_bytes(fixture.replace("\n", newline).encode())
                try:
                    self.request("?logout=1")
                    token, _ = self.login()
                    status, _, body = self.request(data=dict(settings, token=token))
                    self.assertEqual((status, body), (200, "1"))
                    saved = config.read_bytes()
                    self.assertIn(marker.replace("\n", newline).encode(), saved)
                    self.assertIn(b"$root_path = __DIR__ . '/data';", saved)
                    result = subprocess.run(
                        [self.php, "-r", "include $argv[1]; echo $CONFIG;", str(config)],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["theme"], "dark")
                    status, _, _ = self.request()
                    self.assertEqual(status, 200)
                finally:
                    config.write_text(original)

    def test_ambiguous_settings_fail_without_overwriting_config(self):
        config = self.root / "config.php"
        original = config.read_text()
        duplicate = original + "$CONFIG = '{\"lang\":\"en\",\"theme\":\"light\"}';\n"
        try:
            config.write_text(duplicate)
            token, _ = self.login()
            status, _, body = self.request(data={
                "ajax": "true", "type": "settings", "token": token,
                "js-language": "en", "js-error-report": "false",
                "js-show-hidden": "false", "js-hide-cols": "false", "js-theme-3": "dark",
            })
            self.assertGreaterEqual(status, 400)
            self.assertNotEqual(body.strip(), "1")
            self.assertEqual(config.read_text(), duplicate)
        finally:
            config.write_text(original)

    def test_multipart_invalid_token_cannot_write(self):
        self.login()
        _, _, body = self.upload("invalid-token", "rejected.txt")
        self.assertEqual(json.loads(body)["status"], "error")
        self.assertFalse((self.root / "data" / "rejected.txt").exists())

    def test_multipart_upload_preserves_filename_dotfiles_and_folders(self):
        token, _ = self.login()
        for filename, fullpath, destination in (
                ("upload.txt", "upload.txt", "upload.txt"),
                (".env", ".env", ".env"),
                ("CASE.TXT", "folder/CASE.TXT", "folder/CASE.TXT")):
            with self.subTest(filename=filename):
                status, _, body = self.upload(token, filename, fullpath)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["status"], "success")
                self.assertEqual((self.root / "data" / destination).read_bytes(), b"uploaded")

    def test_multipart_fullpath_cannot_change_allowed_extension(self):
        config = self.root / "config.php"
        original = config.read_text()
        try:
            config.write_text(original + "$allowed_upload_extensions = 'txt';\n")
            token, _ = self.login()
            status, _, body = self.upload(token, "safe.txt", "shell.php")
            self.assertEqual(status, 200)
            response = json.loads(body)
            self.assertFalse((self.root / "data" / "shell.php").is_file())
            if response["status"] == "success":
                self.assertEqual((self.root / "data" / "safe.txt").read_bytes(), b"uploaded")
            _, _, body = self.upload(token, "disallowed.php", "new-folder/file.txt")
            self.assertEqual(json.loads(body)["status"], "error")
            self.assertFalse((self.root / "data" / "new-folder").exists())
        finally:
            config.write_text(original)

    def test_upload_rejects_traversal_and_symlink_targets(self):
        token, _ = self.login()
        outside = self.root / "outside"
        outside.mkdir(exist_ok=True)
        linked = self.root / "data" / "escape"
        linked.symlink_to(outside, target_is_directory=True)
        for fullpath in ("../outside/escape.txt", "escape/escape.txt",
                         "escape/new-directory/escape.txt"):
            with self.subTest(fullpath=fullpath):
                _, _, body = self.upload(token, "escape.txt", fullpath)
                self.assertEqual(json.loads(body)["status"], "error")
                self.assertEqual(list(outside.iterdir()), [])
        target = self.root / "data" / "link.txt"
        target.symlink_to(outside / "untouched")
        _, _, body = self.upload(token, "link.txt")
        self.assertEqual(json.loads(body)["status"], "error")
        self.assertFalse((outside / "untouched").exists())
        part = self.root / "data" / "chunk.txt.part"
        part.symlink_to(outside / "chunk")
        _, _, body = self.upload(token, "chunk.txt", chunk=(0, 2))
        self.assertEqual(json.loads(body)["status"], "error")
        self.assertFalse((outside / "chunk").exists())

    def test_chunk_upload_assembles_in_original_folder(self):
        token, _ = self.login()
        for index, content in enumerate((b"first-", b"second")):
            _, _, body = self.upload(
                token, "chunked.txt", "chunks/chunked.txt", content, (index, 2))
            self.assertEqual(json.loads(body)["status"], "success")
        destination = self.root / "data" / "chunks" / "chunked.txt"
        self.assertEqual(destination.read_bytes(), b"first-second")
        _, _, body = self.upload(
            token, "chunked.txt", "chunks/chunked.txt", b"conflict", (0, 1))
        self.assertEqual(json.loads(body)["status"], "success")
        self.assertEqual(destination.read_bytes(), b"first-second")
        renamed = list(destination.parent.glob("chunked_*.txt"))
        self.assertEqual(len(renamed), 1)
        self.assertEqual(renamed[0].read_bytes(), b"conflict")

    def test_chunk_upload_preserves_existing_parts_and_dotfile_names(self):
        token, _ = self.login()
        partial = self.root / "data" / "kept.txt.part"
        partial.write_bytes(b"existing user data")
        _, _, body = self.upload(token, "kept.txt", chunk=(0, 1))
        self.assertEqual(json.loads(body)["status"], "error")
        self.assertEqual(partial.read_bytes(), b"existing user data")
        self.assertFalse((self.root / "data" / "kept.txt").exists())
        dotfile = self.root / "data" / ".env"
        dotfile.write_bytes(b"original")
        _, _, body = self.upload(token, ".env", content=b"new", chunk=(0, 1))
        self.assertEqual(json.loads(body)["status"], "success")
        self.assertEqual(dotfile.read_bytes(), b"original")
        renamed = list(dotfile.parent.glob(".env_*"))
        self.assertEqual(len(renamed), 1)
        self.assertEqual(renamed[0].read_bytes(), b"new")

    def test_interleaved_or_missing_chunks_cannot_corrupt_upload(self):
        token, _ = self.login()
        _, _, body = self.upload(
            token, "interleaved.txt", content=b"first-", chunk=(0, 2), upload_id="first")
        self.assertEqual(json.loads(body)["status"], "success")
        for index in (0, 1):
            _, _, body = self.upload(
                token, "interleaved.txt", content=b"wrong", chunk=(index, 2), upload_id="second")
            self.assertEqual(json.loads(body)["status"], "error")
        partial = self.root / "data" / "interleaved.txt.part"
        self.assertEqual(partial.read_bytes(), b"first-")
        _, _, body = self.upload(
            token, "interleaved.txt", content=b"second", chunk=(1, 2), upload_id="first")
        self.assertEqual(json.loads(body)["status"], "success")
        self.assertEqual((self.root / "data" / "interleaved.txt").read_bytes(), b"first-second")
        _, _, body = self.upload(token, "missing.txt", chunk=(1, 2), upload_id="missing")
        self.assertEqual(json.loads(body)["status"], "error")
        self.assertFalse((self.root / "data" / "missing.txt.part").exists())

    def test_failed_chunk_size_limit_allows_a_fresh_upload(self):
        config = self.root / "config.php"
        original = config.read_text()
        try:
            config.write_text(original + "$max_upload_size_bytes = 5;\n")
            token, _ = self.login()
            _, _, body = self.upload(
                token, "limited.txt", content=b"abc", chunk=(0, 2), upload_id="old")
            self.assertEqual(json.loads(body)["status"], "success")
            _, _, body = self.upload(
                token, "limited.txt", content=b"def", chunk=(1, 2), upload_id="old")
            self.assertEqual(json.loads(body)["status"], "error")
            self.assertFalse((self.root / "data" / "limited.txt.part").exists())
            _, _, body = self.upload(
                token, "limited.txt", content=b"ok", chunk=(0, 1), upload_id="new")
            self.assertEqual(json.loads(body)["status"], "success")
            self.assertEqual((self.root / "data" / "limited.txt").read_bytes(), b"ok")
        finally:
            config.write_text(original)

    def test_filename_markup_is_escaped_and_search_is_accessible(self):
        self.login()
        filename = 'test" onmouseover="alert(1).txt'
        (self.root / "data" / filename).write_text("xss fixture")
        status, _, body = self.request()
        self.assertEqual(status, 200)
        self.assertNotIn('title="' + filename + '"', body)
        self.assertIn("test&quot; onmouseover=&quot;alert(1).txt", body)
        status, _, body = self.request(
            "?p=&" + urllib.parse.urlencode({"edit": filename}))
        self.assertEqual(status, 200)
        title = re.search(r"<title>(.*?)</title>", body, re.S).group(1)
        self.assertNotIn('"', title)
        self.assertIn("&quot;", title)
        self.assertNotIn("dropdown-menu-right", body)
        self.assertIn('aria-label="Advanced Search"', body)

    def test_url_upload_rejects_private_and_unsupported_targets(self):
        token, _ = self.login()
        targets = (
            "http://127.0.0.1/file.txt", "http://[::1]/file.txt",
            "http://169.254.169.254/file.txt", "http://2130706433/file.txt",
            "http://127.1/file.txt", "file:///etc/passwd",
            "http://user:pass@example.com/file.txt",
            "https://example.com:8080/file.txt",
        )
        for url in targets:
            with self.subTest(url=url):
                _, _, body = self.request(data={
                    "ajax": "true", "type": "upload", "token": token, "uploadurl": url})
                self.assertIn("fail", json.loads(body))
        self.assertFalse((self.root / "data" / "file.txt").exists())

    def test_64bit_file_sizes_do_not_spawn_shell_commands(self):
        program = r'''
namespace Regression;
if (PHP_INT_SIZE < 8) { echo 'SKIP'; exit; }
function exec() { throw new \RuntimeException('Unexpected shell execution'); }
$source = file_get_contents($argv[1]);
if (!preg_match('/^function fm_get_size\(\$file\)\n\{.*?^\}/ms', $source, $match)) {
    throw new \RuntimeException('Cannot locate fm_get_size');
}
eval('namespace Regression; ' . $match[0]);
foreach (array('empty-size' => 0, 'quoted file\' é.txt' => 7, 'large' => 3221225489) as $name => $expected) {
    if (fm_get_size($argv[2] . '/' . $name) !== $expected) {
        throw new \RuntimeException('Incorrect size: ' . $name);
    }
}
echo 'PASS';
'''
        for name, size in (("empty-size", 0), ("quoted file' é.txt", 7), ("large", 3221225489)):
            with open(self.root / "data" / name, "wb") as file:
                file.truncate(size)
        result = subprocess.run(
            [self.php, "-r", program, str(self.root / "tinyfilemanager.php"),
             str(self.root / "data")], capture_output=True, text=True,
        )
        if result.stdout == "SKIP":
            self.skipTest("64-bit filesize fast path requires 64-bit PHP")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
