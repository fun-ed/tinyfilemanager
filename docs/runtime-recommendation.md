# Production runtime 建議

查核日期：2026-10-17。這是依官方文件與目前程式結構提出的 recommendation，不是部署完成紀錄或效能實測；本次不把既有 Dockerfile 切換到另一個 runtime。

## 結論

**這個 repo 優先選 FrankenPHP classic mode，使用它內建的 Caddy。暫不使用 FrankenPHP worker mode，也不為了導入 RoadRunner 而重寫應用程式。**

原因是維護與除錯成本，而不是已證明的 RAM 或 CPU 優勢。`tinyfilemanager.php` 是傳統 PHP 單檔程式，依賴 superglobals、PHP session、全域常數/函式、直接 `header()`/輸出與 `exit()`。FrankenPHP 可以用一般請求模式承接；RoadRunner 的官方 HTTP 整合需要 PHP worker、持續迴圈與 request/response 適配，這些目前都不存在。[1][2][3]

## 版本基準

- FrankenPHP 最新 stable 為 **v1.13.1**，GitHub release 發布於 2026-10-16。它修正 v1.13.0 的 worker、CLI 與 graceful-shutdown 問題，不建議把剛好較舊的 v1.13.0 當新部署基準。[4]
- RoadRunner 最新 stable 為 **v3.0.0**，GitHub release 發布於 2026-10-09。這是有 config/API migration 的版本；不要把 v2025.1.15 當成截至本次查核的最新版。[5]
- 部署時應選擇仍受支援、完成相容性測試的 PHP 分支，並固定官方映像的實際 tag 與 digest。此 repo 的本地測試環境是 PHP 8.5.11，不代表已測過 FrankenPHP 的 PHP 8.5 映像。不要猜測未查證的 image tag。

## 選項比較

| 面向 | FrankenPHP classic | RoadRunner |
| --- | --- | --- |
| 現有程式適配 | 不需要先建立長駐 application worker；仍須驗證 sessions、上傳、下載與設定寫入。 | 需建立 worker 與 Composer/PSR HTTP 適配，並重新處理輸出、終止與請求狀態。 |
| 維護成本 | 一個整合 Caddy/PHP 的服務；依現有 PHP 邏輯查錯。 | Go server、PHP process pool、worker 協定、HTTP bridge 與應用程式生命週期都需維護。 |
| 除錯 | 先沿單次請求追蹤 PHP 與 Caddy logs；不必先排除 application worker 的跨請求狀態殘留。 | 官方有 debug mode 與 worker/pool 控制，但需分辨 server、worker、協定及應用層問題。 |
| 資源控制 | `num_threads`、`max_threads`、等待時間與 PHP memory limit；仍須控制容器總記憶體。 | `num_workers`、dynamic allocator、worker memory supervisor、TTL 與 queue/admission controls。 |
| 資源勝負 | 未對這個應用實測，不能宣稱比較省 RAM 或較快。 | 同樣不能只依一般 framework benchmark 宣稱比較省資源。 |
| 較合適的後續情境 | 保留單檔管理工具，以低維護成本提供一般 HTTP 請求。 | 已有 PSR/framework worker 適配，或確實需要 jobs、RPC、多種 worker plugin 與 pool 運作能力。 |

RoadRunner 的 worker isolation 是 process 層級；這不等於目前的 PHP script 可以直接放進持續迴圈，也不等於同一 worker 的 application state 會自動在每個請求重建。[2][6]

## 為什麼先不開 worker mode

FrankenPHP worker mode 的入口也必須呼叫 `frankenphp_handle_request()`。雖然 request superglobals 會更新，應用程式本身仍是長駐的。不能直接把整支 TinyFileManager 反覆 `require`，忽略函式/常數重複宣告、session/全域狀態、`exit()` 與清理行為。[3]

這個工具的成本多半還涉及 filesystem listing、檔案傳輸與遠端 I/O。沒有先量測，就為了省 bootstrap 改成長駐 worker，會增加維護面積，未必改善主要瓶頸。

## Caddy 是否另外部署

### 單機、單一服務

建議拓撲是 `client → FrankenPHP 內建 Caddy → classic PHP`。內建 Caddy 已能做 HTTPS、HTTP serving 與 routing；再加一個相同職責的 Caddy instance 通常不是最低維護成本。[1][7]

### 已有共用 ingress 或多個服務

可以使用 `client → 共用 Caddy edge → 私有 FrankenPHP backend`。保留既有 edge 才有理由多一層，例如統一網域、TLS 或存取政策；backend 僅監聽 loopback/private network，不直接對公網開放。不要只為了架構看起來完整而重複 TLS termination。

- `trusted_proxies` 僅列出實際可信的 proxy IP/CIDR，不信任全部來源。[7][8]
- 本程式會自行讀取 forwarded headers。Caddy 的 proxy trust 設定不能取代應用層檢查；在可信邊界移除/重建客戶端帶入的 `X-Forwarded-*`，不要讓外部任意宣稱 HTTPS 或來源 IP。
- Caddy admin API 保持私有，憑證資料使用持久化儲存。不要在公開網路暴露管理介面。
- edge 與 backend 的 body size、upload timeout 必須一致；重載或更新不能直接中斷尚未完成的上傳。

## Production 安全基線

1. **把管理資料與 web root 分開。** FrankenPHP `php_server` 預設含 static file server。不能把整個 repo 或上傳目錄當成公開檔案站，否則可能繞過管理員驗證；也不能讓上傳的 `.php` 直接執行。只允許指定管理入口與必要靜態資源，資料下載走授權 handler；不需要的 `file_server` 應關閉。[1][9]
2. `.git/`、`.serena/`、`.agents/`、`.omp/`、`docs/`、config、備份與 session 檔都不應成為可下載資源。資料放在 web root 外時，既有 DirectLink 不會自然繼續可用；應明確停用或另行設計授權傳輸，而不是把資料重新暴露出去。
3. 使用 production PHP settings、關閉畫面上的錯誤細節、保留必要的錯誤紀錄，安裝本程式實際需要的 Fileinfo、cURL、Zip/Phar 等 extension。PHP 設定與 reverse proxy 限制要配合應用程式的大小/時間上限。[7]
4. 設定寫入採原子替換，容器要提供可寫入的目錄與正確權限。不要假設 bind-mount 單一 `config.php` 檔案後仍能原子 rename；若部署策略不允許寫入，應清楚拒絕設定儲存，而不是放寬 code/config 權限。
5. 官方 FrankenPHP performance 文件建議 production 優先使用 glibc build，而不是把 Alpine 的較小 image size 當成較低執行成本的保證。[9]

## 低資源主機怎麼起步

- 先固定小型 classic thread 上限，例如以 **2 threads** 作為低併發測試起點，不視為通用最佳值。長下載或 60 秒 URL fetch 會占用 PHP 處理容量，需同時測試一般操作是否仍可回應。
- 依實際流量設定 `num_threads`、`max_threads` 與等待時間。不要直接採用 CPU 倍數或無上限 autoscaling 作為省資源配置。
- 官方建議以 `max_threads × memory_limit < available_memory` 作為穩定性檢核，但這不是完整 RSS 公式；仍需預留 Caddy、Go runtime、OPcache、TLS、buffers、作業系統與同機服務的空間。[9]
- 開啟並驗證 OPcache。不要為單檔程式引入框架的 autoloader/preload 優化。避免無需求的 worker、第二層 proxy、過量 access logs 或 background services。

### 上線前的比較方法

在相同主機、PHP extension、資料集、TLS 與併發條件下，量測 idle/peak RSS 或 container memory、CPU、p95 latency、timeout/error rate 與下載期間的其他請求延遲。案例至少包含登入/列表、上千檔案列表、編輯、chunk upload、大檔下載、URL upload、並行請求及重啟/重載。

先驗證 FrankenPHP classic 符合預算。只有它不符合具體 SLO，而 RoadRunner 的適配成本有可量測收益時，才做 RoadRunner PoC。這次沒有執行兩者的安裝、benchmark、production TLS 或重載驗證，不能把 recommendation 寫成已證實的資源節省。

## 官方來源

1. [FrankenPHP configuration：php_server、classic threads、static serving](https://frankenphp.dev/docs/config/)
2. [RoadRunner PHP worker 與 Composer/PSR-7 整合](https://docs.roadrunner.dev/docs/php-worker/worker)
3. [FrankenPHP worker lifecycle、superglobals 與 failure handling](https://frankenphp.dev/docs/worker/)
4. [FrankenPHP v1.13.1 release](https://github.com/php/frankenphp/releases/tag/v1.13.1)
5. [RoadRunner v3.0.0 release 與 migration](https://github.com/roadrunner-server/roadrunner/releases/tag/v3.0.0)
6. [RoadRunner worker pool：debug、memory、TTL 與 allocation limits](https://docs.roadrunner.dev/docs/php-worker/pool)
7. [FrankenPHP production deployment、TLS 與 reverse proxy](https://frankenphp.dev/docs/production/)
8. [Caddy trusted proxies](https://caddyserver.com/docs/caddyfile/options#trusted-proxies)
9. [FrankenPHP performance：glibc、threads、memory 與 file_server](https://frankenphp.dev/docs/performance/)
