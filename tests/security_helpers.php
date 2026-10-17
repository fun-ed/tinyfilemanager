<?php

function security_test_check($condition, $message)
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

function security_test_extract_declaration($source, $declarationId, $name)
{
    $tokens = token_get_all($source);
    $offset = 0;
    foreach ($tokens as $index => $token) {
        $tokenText = is_array($token) ? $token[1] : $token;
        if (is_array($token) && $token[0] === $declarationId) {
            $nameIndex = $index + 1;
            while (isset($tokens[$nameIndex]) && is_array($tokens[$nameIndex]) && in_array($tokens[$nameIndex][0], array(T_WHITESPACE, T_COMMENT, T_DOC_COMMENT), true)) {
                $nameIndex++;
            }
            if ($declarationId === T_FUNCTION && isset($tokens[$nameIndex]) && $tokens[$nameIndex] === '&') {
                $nameIndex++;
            }
            if (isset($tokens[$nameIndex]) && is_array($tokens[$nameIndex]) && $tokens[$nameIndex][0] === T_STRING && $tokens[$nameIndex][1] === $name) {
                $start = $offset;
                $braceDepth = 0;
                $bodyStarted = false;
                $bodyOffset = $offset;
                for ($bodyIndex = $index; $bodyIndex < count($tokens); $bodyIndex++) {
                    $bodyToken = $tokens[$bodyIndex];
                    $bodyText = is_array($bodyToken) ? $bodyToken[1] : $bodyToken;
                    if (!is_array($bodyToken) && $bodyText === '{') {
                        $braceDepth++;
                        $bodyStarted = true;
                    } elseif (!is_array($bodyToken) && $bodyText === '}') {
                        $braceDepth--;
                        if ($bodyStarted && $braceDepth === 0) {
                            return substr($source, $start, $bodyOffset + strlen($bodyText) - $start);
                        }
                    }
                    $bodyOffset += strlen($bodyText);
                }
                throw new RuntimeException('Unclosed declaration: ' . $name);
            }
        }
        $offset += strlen($tokenText);
    }
    throw new RuntimeException('Declaration not found: ' . $name);
}

function security_test_config_value($source)
{
    foreach (token_get_all($source) as $index => $token) {
        if (!is_array($token) || $token[0] !== T_VARIABLE || $token[1] !== '$CONFIG') {
            continue;
        }
        $tokens = token_get_all($source);
        $next = $index + 1;
        while (isset($tokens[$next]) && is_array($tokens[$next]) && in_array($tokens[$next][0], array(T_WHITESPACE, T_COMMENT, T_DOC_COMMENT), true)) {
            $next++;
        }
        if (!isset($tokens[$next]) || $tokens[$next] !== '=') {
            continue;
        }
        $next++;
        while (isset($tokens[$next]) && is_array($tokens[$next]) && in_array($tokens[$next][0], array(T_WHITESPACE, T_COMMENT, T_DOC_COMMENT), true)) {
            $next++;
        }
        if (!isset($tokens[$next]) || !is_array($tokens[$next]) || $tokens[$next][0] !== T_CONSTANT_ENCAPSED_STRING) {
            throw new RuntimeException('CONFIG value is not a string literal.');
        }
        return eval('return ' . $tokens[$next][1] . ';');
    }
    throw new RuntimeException('CONFIG assignment not found.');
}

$source = file_get_contents(dirname(__DIR__) . '/tinyfilemanager.php');
if ($source === false) {
    throw new RuntimeException('Could not read tinyfilemanager.php.');
}
$definitions = array(
    security_test_extract_declaration($source, T_CLASS, 'FM_Config'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_is_public_ip'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_resolve_public_url_host'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_validate_remote_url'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_url_upload_filename'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_fetch_url_to_file'),
    security_test_extract_declaration($source, T_FUNCTION, 'fm_isvalid_filename')
);
eval(implode("\n", $definitions));

foreach (array('8.8.8.8', '1.1.1.1', '2606:4700:4700::1111', '2001:4860:4860::8888') as $ip) {
    security_test_check(fm_is_public_ip($ip), 'Expected a public address: ' . $ip);
}
foreach (array(
    '0.0.0.0', '10.0.0.1', '100.64.0.1', '127.0.0.1', '169.254.169.254', '172.16.0.1',
    '192.0.2.1', '192.168.1.1', '168.63.129.16', '198.18.0.1', '198.51.100.1', '203.0.113.1', '224.0.0.1',
    '240.0.0.1', '::', '::1', '::ffff:8.8.8.8', '64:ff9b::808:808', '2001:db8::1',
    '2001:2::1', '2002:0808:0808::1', '3fff::1', '5f00::1', 'fc00::1', 'fe80::1', 'ff02::1'
) as $ip) {
    security_test_check(!fm_is_public_ip($ip), 'Expected a non-public address: ' . $ip);
}

$details = null;
$error = '';
security_test_check(fm_validate_remote_url('http://8.8.8.8:80/file.txt', $details, $error), 'Public literal HTTP URL should validate.');
security_test_check($details['address'] === '8.8.8.8' && $details['port'] === 80, 'Validated URL should expose the pinned address and port.');
security_test_check(fm_validate_remote_url('https://[2606:4700:4700::1111]/file.txt', $details, $error), 'Public literal IPv6 HTTPS URL should validate.');
foreach (array(
    'file://8.8.8.8/file.txt', 'http://user:pass@8.8.8.8/file.txt', 'http://8.8.8.8:8080/file.txt',
    'https://8.8.8.8:80/file.txt', 'http://127.0.0.1/file.txt', 'http://169.254.169.254/latest/meta-data',
    'http://2130706433/file.txt', 'http://[::ffff:8.8.8.8]/file.txt'
) as $url) {
    security_test_check(!fm_validate_remote_url($url, $details, $error), 'Expected URL to be rejected: ' . $url);
}
security_test_check(fm_url_upload_filename('https://example.invalid/path/file%2Bname.txt?name=ignored.txt', 'txt') === 'file+name.txt', 'URL filename should use raw percent decoding and ignore the query.');
security_test_check(fm_url_upload_filename('https://example.invalid/.env') === '.env', 'Dotfile URL basename should be preserved.');
security_test_check(fm_url_upload_filename(str_repeat('x', 4097)) === false, 'URL filename parsing should reject oversized URLs before parsing.');
foreach (array(
    'https://example.invalid/path%2Fescape.txt', 'https://example.invalid/path%5Cescape.txt',
    'https://example.invalid/path%00name.txt', 'https://example.invalid/file.exe'
) as $url) {
    security_test_check(fm_url_upload_filename($url, 'txt') === false, 'Expected URL filename to be rejected: ' . $url);
}

$directory = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'tfm-security-' . bin2hex(random_bytes(6));
if (!mkdir($directory, 0700)) {
    throw new RuntimeException('Could not create test directory.');
}
try {
    $configPath = $directory . DIRECTORY_SEPARATOR . 'config.php';
    $config = new ReflectionClass('FM_Config');
    $settings = $config->newInstanceWithoutConstructor();
    $settings->data = array('literal' => '$keep\\backslash', 'theme' => 'dark');
    $GLOBALS['config_file'] = $configPath;

    $lfSource = "<?php\n// Keep this sample comment.\n\$CONFIG = '{\n  \"lang\": \"en\",\n  \"old\": \"multiline\"\n}';\n\$deployment_setting = 'preserve';\n";
    file_put_contents($configPath, $lfSource);
    chmod($configPath, 0640);
    security_test_check($settings->save(), 'LF config save should succeed.');
    $saved = file_get_contents($configPath);
    security_test_check(strpos($saved, '// Keep this sample comment.') !== false && strpos($saved, "\$deployment_setting = 'preserve';") !== false, 'Config comments and deployment variables should remain.');
    security_test_check(json_decode(security_test_config_value($saved), true) === $settings->data, 'Saved JSON should preserve literal dollar signs and backslashes.');
    security_test_check((fileperms($configPath) & 07777) === 0640, 'Config mode should remain unchanged.');

    $crlfSource = "<?php\r\n// CRLF stays.\r\n\$CONFIG = '{\"old\": true}';\r\n\$deployment_setting = 'also preserved';\r\n";
    file_put_contents($configPath, $crlfSource);
    security_test_check($settings->save(), 'CRLF config save should succeed.');
    $saved = file_get_contents($configPath);
    security_test_check(strpos($saved, "// CRLF stays.\r\n") !== false && preg_match('/(?<!\r)\n/', $saved) !== 1, 'CRLF line endings should be preserved.');
    security_test_check(strpos($saved, "\$deployment_setting = 'also preserved';") !== false, 'Unrelated CRLF deployment variable should remain.');

    $missingSource = "<?php\r\n// No config assignment.\r\n\$deployment_setting = 'keep';\r\n";
    file_put_contents($configPath, $missingSource);
    security_test_check($settings->save(), 'Config without an assignment should gain one.');
    $saved = file_get_contents($configPath);
    security_test_check(strpos($saved, '$CONFIG = ') !== false && strpos($saved, "// No config assignment.\r\n") !== false, 'Missing assignment should be inserted after the PHP open tag without losing comments.');
    security_test_check(json_decode(security_test_config_value($saved), true) === $settings->data, 'Inserted config assignment should contain valid JSON.');

    file_put_contents($configPath, $source);
    security_test_check($settings->save(), 'Settings must also save a full application file containing interpolated PHP strings.');
    security_test_check(json_decode(security_test_config_value(file_get_contents($configPath)), true) === $settings->data, 'Application-file save should update only the configuration literal.');

    foreach (array(
        "<?php\n\$CONFIG = 'first';\n\$CONFIG = 'second';\n",
        "<?php\n\$CONFIG = getenv('DANGEROUS');\n",
        "<?php\nif (true) { \$CONFIG = 'nested'; }\n",
        "<?php\ndeclare(strict_types=1);\n\$deployment = 'keep';\n",
        "<?php\nnamespace Deployment;\n\$deployment = 'keep';\n"
    ) as $unsafeSource) {
        file_put_contents($configPath, $unsafeSource);
        $before = hash_file('sha256', $configPath);
        security_test_check(!$settings->save(), 'Unsafe config should fail closed: ' . $unsafeSource);
        security_test_check(hash_file('sha256', $configPath) === $before, 'Failed config save must leave original bytes intact.');
    }
    if (getenv('TFM_LIVE_FETCH_TESTS') === '1') {
        security_test_check(function_exists('curl_init'), 'Live URL checks require PHP cURL.');
        $temporary = $directory . DIRECTORY_SEPARATOR . 'download.tmp';
        touch($temporary);
        security_test_check(fm_fetch_url_to_file('https://example.com/', $temporary, 65536, $error), 'Public HTTPS download failed: ' . $error);
        security_test_check(filesize($temporary) > 0 && filesize($temporary) <= 65536, 'Public HTTPS download must remain within its byte cap.');
        touch($temporary);
        security_test_check(!fm_fetch_url_to_file('https://example.com/', $temporary, 1, $error), 'A response exceeding the streamed byte cap must fail.');
        security_test_check(strpos($error, 'size limit') !== false && !file_exists($temporary), 'Oversized download must report the cap and remove its temporary file.');
        touch($temporary);
        security_test_check(!fm_fetch_url_to_file('https://github.com/dunglas/frankenphp', $temporary, 65536, $error), 'Redirect responses must not be followed.');
        security_test_check(strpos($error, 'Redirect') !== false && !file_exists($temporary), 'Redirect rejection must be explicit and clean up the download: ' . $error);
        echo "live URL fetch regressions passed\n";
    }
} finally {
    foreach (scandir($directory) as $entry) {
        if ($entry !== '.' && $entry !== '..') {
            @unlink($directory . DIRECTORY_SEPARATOR . $entry);
        }
    }
    @rmdir($directory);
}

echo "security helper regressions passed\n";
