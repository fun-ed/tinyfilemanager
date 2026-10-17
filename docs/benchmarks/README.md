# FrankenPHP classic benchmark

Measured on 2026-10-17 at 11:30 UTC. This is a small, bounded benchmark of TinyFileManager 3.0.0, not a production capacity claim or a comparison with RoadRunner.

## Setup and method

- Application source: release `3.0.0`, commit `1fb310660931259c1fc394c85eea0c9d7c99e6f2`.
- Runtime: FrankenPHP 1.13.1, PHP 8.5.11 ZTS, Debian 13 trixie container on a shared x86_64 Linux VPS.
- Container limits: 1 logical CPU, 1 GiB RAM, 2 PHP threads. Classic mode, not worker mode.
- Locale: `zh-TW`, with the bundled translation catalog available to the application's working directory.
- Workload: authenticated `GET /index.php?p=` against an empty managed directory. Each response contained the authenticated page marker and approximately 49,098 bytes of HTML.
- Client: Python standard library on the same host, outside the application container's CPU/memory limit. HTTP/1.1 connections were reused over IPv4 loopback; TLS, reverse proxy, SSH tunnel, internet latency and browser/CDN rendering were excluded.
- Four independently authenticated sessions prevented one PHP session lock from serializing every client. Credentials, cookies and response bodies were not included in the results artifact.
- Twenty warm-up requests preceded three sequential cases: concurrency 1, 2 and 4, with 100 measured requests each. Each worker issued its next request only after reading the previous response completely. No rate cap, retries or think time; each case had a 15-second scheduling deadline and 3-second socket timeout.
- Login setup and logout were outside the timing. Managed files and settings were not modified, and the service was not restarted. Normal session-file updates and a private measurement artifact were allowed.

## Results

| Concurrent clients | Requests | Duration | Requests/s | p50 | p95 | Maximum | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 100 | 11.76 s | 8.50 | 114.02 ms | 150.73 ms | 216.71 ms | 0 |
| 2 | 100 | 12.93 s | 7.73 | 246.18 ms | 363.73 ms | 410.85 ms | 0 |
| 4 | 100 | 12.69 s | 7.88 | 496.54 ms | 660.63 ms | 707.16 ms | 0 |

Throughput is completed requests divided by case wall time, including worker coordination. Latency covers request submission through complete response-body reading. p50 is the median; p95 is the nearest-rank 95th percentile of 100 requests. These are one short sample per concurrency level, not averages across repeated trials.

| Concurrent clients | Container CPU | Highest sampled memory.current | CPU throttled time delta |
| --- | --- | --- | --- |
| 1 | 97.03% | 25.30 MiB | 0.08 s |
| 2 | 100.09% | 25.98 MiB | 12.73 s |
| 4 | 100.20% | 32.70 MiB | 13.72 s |

CPU comes from the container cgroup `cpu.stat` usage delta divided by wall time; 100% means one logical CPU. Short-window accounting and scheduling can yield values slightly above 100%. Throttled time is the cgroup counter delta, not added request latency or an error count.

Memory is `memory.current`, sampled every 10 ms and at case boundaries. It includes charged page cache and is not the same as Docker stats' working-set display. Samples can miss brief peaks; this is not the container's lifetime memory peak or the RAM needed for uploads and archives. Container healthcheck work is included in cgroup resource counters.

## Loopback deployment boundary

The measured deployment uses a separate, host-networked FrankenPHP container, not the repository's legacy PHP development-server image. Its effective Caddy configuration sets `admin off`, `auto_https off` and `persist_config off` globally. The HTTP site uses `http://:18080` with an explicit `bind 127.0.0.1`; it does not create a listener on all interfaces. Only `/` and `/index.php` reach PHP; other paths return 404.

Disabling the admin API avoids creating an unauthenticated configuration endpoint on the host's loopback interface. Disabling automatic HTTPS avoids automatic certificate management and HTTP-to-HTTPS redirect listeners. No Docker ports are published. Host networking shares the host network namespace and is not network isolation.

The effective configuration and `ss` output were checked after deployment and rechecked during documentation: the service was healthy and its port-18080 listener was exactly `127.0.0.1:18080`. The file-only entry route, immutable code/config and separate managed-data/session mounts are deliberate deployment boundaries, not guarantees that every application file operation is safe.

Useful read-only checks on a Linux deployment host:

```sh
docker inspect --format '{{.State.Health.Status}} {{.HostConfig.NetworkMode}}' tinyfilemanager-classic
docker exec tinyfilemanager-classic cat /etc/frankenphp/Caddyfile
ss -H -ltnp 'sport = :18080'
```

No service, ingress, DNS or firewall configuration was changed for this documentation update. A future public TLS/reverse-proxy deployment needs a separate review of ingress exposure, trusted forwarded headers and secure cookies.

## Interpretation and limits

The single-client sample had a 114 ms median server-response time. More concurrent clients did not increase throughput: the application used approximately its full one-CPU allowance, with substantial throttling in the concurrent cases. Keep the present resource limits for occasional administration unless an actual latency or workload requirement calls for another test. This result does not establish that FrankenPHP itself is the expensive part, or that worker mode or RoadRunner would help.

Code inspection shows that `lng()` calls `fm_get_translations()` for every lookup. The latter caches catalog bytes within a request but still decodes JSON and rebuilds language maps per call. This is a profiling candidate, not a measured attribution of CPU time; no application optimization was made for this benchmark.

Not measured: cold starts, sustained load, repeated-trial variance, large directories, uploads/downloads, archives, authentication throughput, a shared-session browser workload, other locales, remote clients or rendered UI latency. The directory contained zero entries, so do not extrapolate these numbers to filesystem-heavy use. There was no PHP-FPM, RoadRunner or worker-mode control run.

After all 300 measured requests, the same container remained healthy without a restart or data changes. Benchmark sessions were logged out. Raw measurement JSON stays in the private deployment verification directory; it is not a repository fixture or a public host inventory.

For future comparisons, keep the source revision, locale, dataset, CPU quota, PHP thread count, session independence, connection reuse and measurement definitions fixed. Repeat cases in varied order before claiming an improvement. See [runtime recommendations](../runtime-recommendation.md) and [the maintenance plan](../issue-plan.md) for the separate deployment and security scope.
