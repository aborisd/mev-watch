# MEV-Watch — deployment readiness report

 MEV-Watch — deployment readiness report

Автор: **aborisd** ·
[Instagram](https://instagram.com/aborisd) ·
[GitHub](https://github.com/aborisd)

---

## 1. Status на сейчас

| Слой | Готовность к 24/7 | Комментарий |
|---|---|---|
| Docker Compose | ✅ | все сервисы с `restart: unless-stopped` |
| Postgres | ✅ | healthcheck работает, схема + TimescaleDB + pg_notify |
| Ingester | ✅ | WS-реконнект с exp backoff, RPC-семафор от 429 |
| Detector | ✅ | отдельный цикл, не блокирует ингест, дедуп на уникальном индексе |
| API | ✅ | 6 эндпоинтов + SSE, CORS открыт |
| Frontend | ✅ | SSR через Next.js standalone, же rewrites на API |
| Caddy (HTTPS) | ✅ | конфиг готов, авто-сертификаты Let's Encrypt |
| Логи | ⚠️ | пухнут неограниченно — **нужно добавить ротацию** |
| Бэкапы Postgres | ❌ | отсутствуют |
| Мониторинг | ❌ | нет внешнего пинга |
| Секреты | ⚠️ | Chainstack-ключ и POSTGRES_PASSWORD надо прокрутить |
| Порт-маппинги | ⚠️ | postgres/api/web торчат наружу — **закрыть** в проде |

**Итого:** код готов, но 5 вещей надо закрыть перед публичным деплоем. Все они перечислены в §3.

---

## 2. TL;DR — три команды до `live`

На Ubuntu 24.04 VPS с установленным Docker:

```bash
git clone <repo> && cd mev-watch
cp .env.example .env && $EDITOR .env       # fill Chainstack, strong pass, domain
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Детали — в §4–§6.

---

## 3. Pre-flight — что поправить в репо до деплоя

### 3.1 Обязательно (MUST)

1. **Прокрутить Chainstack ключ.** Текущий засветился в чате и в истории коммитов — завести новый в [Chainstack Console](https://console.chainstack.com/), старый удалить.
2. **Сильный `POSTGRES_PASSWORD`.** Дефолт `mev_change_me` — заменить на 32-символьный случайный (например `openssl rand -base64 32`).
3. **Закрыть порты в проде.** Сейчас `postgres:5432`, `api:8001`, `web:3000` торчат на host'е — для локалки ок, для паблик-VPS нет. Создать `docker-compose.prod.yml` с override: убрать все `ports:` кроме caddy (80/443). Доступ к API — только через `https://<domain>/api/*`.
4. **Реальный домен в `CADDY_DOMAIN`.** Заменить `:80` на `mev.yourdomain.com` — Caddy автоматически получит Let's Encrypt сертификат.

### 3.2 Желательно (SHOULD)

5. **Ротация логов** — добавить в каждый сервис compose:
   ```yaml
   logging:
     driver: json-file
     options:
       max-size: "10m"
       max-file: "3"
   ```
   Без этого `docker logs` может занять гигабайты за неделю.

6. **Фиксировать версии образов.** Сейчас `timescale/timescaledb:latest-pg16`, `caddy:2-alpine`, `node:20-alpine` — в проде лучше pinnить конкретные теги.

7. **Бэкап-сервис** — добавить контейнер с cron + `pg_dump` → `./backups/YYYY-MM-DD.sql.gz`, с ретеншеном 7 дней. См. пример в §8.

### 3.3 Потом (NICE TO HAVE)

- `containrrr/watchtower` для авто-подхвата новых образов при `docker push`
- `fail2ban` на SSH уровнем выше
- Uptime-монитор (healthchecks.io, бесплатно)

---

## 4. VPS — что брать

**Рекомендация: Hetzner CPX21** — €7.05/мес, 3 vCPU, 4 GB RAM, 80 GB NVMe, 20 TB трафика. Локация: Falkenstein или Helsinki (низкая задержка до Chainstack EU).

Альтернативы:
- Hetzner CPX11 (€4.59/мес, 2 vCPU, 2 GB) — минимум; если бэкфилл 50k блоков запустишь — упрёшься в память
- DigitalOcean Basic 2GB ($12/мес) — дороже но с хорошим UI
- Contabo VPS-S (€4.50/мес, 4 vCPU, 8 GB) — дёшево, но хуже сеть
- Vultr Cloud Compute (от $6/мес) — нормальный middle ground

**Обязательно:** Ubuntu 24.04 LTS, SSH-ключ (не пароль), static IPv4 включён.

---

## 5. Первоначальная настройка сервера

```bash
# подключение
ssh root@<VPS_IP>

# базовая гигиена
apt update && apt upgrade -y
apt install -y curl ca-certificates ufw fail2ban

# Docker Engine (official script)
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# пользователь для проекта (не root под докером)
adduser --disabled-password --gecos "" mev
usermod -aG docker mev
mkdir -p /home/mev/.ssh
cp /root/.ssh/authorized_keys /home/mev/.ssh/
chown -R mev:mev /home/mev/.ssh
chmod 700 /home/mev/.ssh && chmod 600 /home/mev/.ssh/authorized_keys

# firewall — только SSH + HTTP + HTTPS
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# опционально: отключить root-вход
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart ssh
```

---

## 6. DNS

В панели регистратора:

```
Type    Name          Value
A       mev           <VPS_IP>        TTL 300
AAAA    mev           <VPS_IPv6>      (если IPv6 есть на VPS)
```

Подождать 1–5 мин, проверить: `dig +short mev.yourdomain.com`.

---

## 7. Деплой

От пользователя `mev`:

```bash
ssh mev@<VPS_IP>
cd ~
git clone https://github.com/aborisd/mev-watch.git
cd mev-watch

cp .env.example .env
vim .env   # заполнить: ETH_WS_URL, ETH_HTTP_URL, POSTGRES_PASSWORD, CADDY_DOMAIN

# DATABASE_URL собираем вручную, чтоб совпал с POSTGRES_PASSWORD
# формат: postgresql://mev:<пароль>@postgres:5432/mev_watch

docker compose up -d
docker compose logs -f ingester   # убедиться что блоки идут
```

Первый запуск Caddy выпустит сертификат — займёт ~30 секунд.

---

## 8. Проверка

```bash
# HTTPS + API
curl https://mev.yourdomain.com/api/v1/health
# → {"ok":true}

curl https://mev.yourdomain.com/api/v1/events?limit=1
# → [{...}]

# данные идут
docker compose exec postgres psql -U mev -d mev_watch -c \
  "SELECT (SELECT COUNT(*) FROM blocks) blocks,
          (SELECT COUNT(*) FROM swaps)  swaps,
          (SELECT COUNT(*) FROM mev_events) mev;"

# дашборд в браузере
open https://mev.yourdomain.com
```

**Чек-лист приёмки:**

- [ ] `curl https://domain/api/v1/health` → 200 `{"ok":true}`
- [ ] `curl https://domain/` → HTML дашборда
- [ ] `docker compose ps` — все 5 сервисов `Up` и `healthy` где применимо
- [ ] `docker compose logs ingester` — каждые 12 с `block_processed`
- [ ] `docker compose logs detector` — периодически `detect_block` с `sandwich=N`
- [ ] Через 10 минут в `mev_events` > 0 строк
- [ ] SSE работает: `curl -N https://domain/api/v1/events/stream`
- [ ] `ufw status` — только 22/80/443 allow
- [ ] `docker port postgres` — ничего не мапится на host (в prod override)

---

## 9. Production hardening (после MVP)

**Бэкапы.** Добавить сервис в compose:

```yaml
backup:
  image: postgres:16-alpine
  depends_on: [postgres]
  volumes:
    - ./backups:/backups
  env_file: .env
  entrypoint: /bin/sh
  command: -c '
    while true; do
      sleep 86400;
      PGPASSWORD=$$POSTGRES_PASSWORD pg_dump -h postgres -U $$POSTGRES_USER -d $$POSTGRES_DB
      | gzip > /backups/$$(date +%Y-%m-%d).sql.gz;
      find /backups -name "*.sql.gz" -mtime +7 -delete;
    done
  '
  restart: unless-stopped
```

Лучше — слать gzip в S3/Backblaze B2 (сразу офсайт). Ссылка на туториал в v2.

**Мониторинг.** Самый простой вариант:

1. Завести чек на [healthchecks.io](https://healthchecks.io) (бесплатно). Получаешь URL вида `https://hc-ping.com/<uuid>`.
2. Добавить cron на VPS:
   ```
   * * * * * curl -fsS https://mev.yourdomain.com/api/v1/health > /dev/null && curl -fsS https://hc-ping.com/<uuid>
   ```
   Если API упадёт — healthchecks пришлёт уведомление в Telegram/Slack/email.

**Авто-обновления.**
- OS-пакеты: `apt install unattended-upgrades`
- Docker-образы: добавить Watchtower-контейнер с `WATCHTOWER_POLL_INTERVAL=3600` — будет подхватывать новые теги раз в час.

**Лимиты ресурсов.** Добавить в каждый Python-сервис:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
```

---

## 10. Known gotchas

1. **Chainstack free tier — 25 RPS**, но бэкфилл может моментально упереться. Не включай `BACKFILL_BLOCKS` > 1000 без платного тарифа, или смирись с ошибками пулов на первые часы.
2. **Reorgs глубже 2 блоков** дают дубликаты в `blocks` (решается `ON CONFLICT DO UPDATE`, но детектор для «переписанного» блока второй раз не прогоняется — проставить `detected_at = NULL` руками если видишь аномалию).
3. **Docker Desktop на Mac** не годится для 24/7 — сон, закрытая крышка, разъёмы. Только Linux VPS.
4. **`POSTGRES_PASSWORD` внутри `DATABASE_URL`.** В `.env` он фигурирует дважды (отдельно и в URL) — обе строки должны быть синхронны.
5. **Порт 8000 на Маке** уже использует другой контейнер — в текущем compose api торчит на 8001. В проде этого порта наружу вообще нет, так что неактуально.

---

## 11. Timeline для деплоя

| Шаг | Время |
|---|---|
| Купить VPS + DNS | 10 мин |
| 5.x — bootstrap сервера | 10 мин |
| Pre-flight изменения в репо (§3.1) | 20 мин |
| Первый `docker compose up -d` + TLS | 5 мин |
| Smoke-тесты (§8 checklist) | 10 мин |
| **Итого до live** | **~1 час** |

Add-ons (бэкапы + мониторинг) — ещё 30 минут, можно после первого дня наблюдения.

---

## 12. Что делать если что-то сломалось

| Симптом | Команда первой помощи |
|---|---|
| Дашборд не открывается | `docker compose logs web caddy` |
| API 500 | `docker compose logs api` + `psql … \dt` |
| Нет новых блоков | `docker compose logs ingester` — WS reconnect или 429? |
| Events перестали появляться | `SELECT MAX(block_number) FROM blocks; SELECT MAX(block_number) FROM mev_events;` — какой сервис отстал |
| Место на диске | `du -sh pgdata caddy_data` + `docker system prune -af` |
| Chainstack отвалился | Проверить квоту в Console; переключиться на backup-провайдера в `.env` и `docker compose restart ingester api` |

---

## 13. После деплоя — что запостить

Для анонса в X/Telegram (суть проекта + что он делает):

> Ship'нул MEV-Watch — live-дашборд sandwich- и JIT-атак на Ethereum.
> Каждое событие — реальные деньги, которые бот снял с обычного свопа на Uniswap.
> Net profit считается честно (gross − gas), API открытый.
>
> [mev.yourdomain.com](https://mev.yourdomain.com) · исходники [github.com/aborisd/mev-watch](https://github.com/aborisd/mev-watch)
