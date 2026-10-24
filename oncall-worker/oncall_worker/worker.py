from __future__ import annotations

import logging
import time
from pathlib import Path

from oncall_worker.alerts import AlertSource, GrafanaAlertSource
from oncall_worker.config import OncallConfig
from oncall_worker.dedup import CooldownStore
from oncall_worker.session import ResponderSession

logger = logging.getLogger(__name__)


class OncallWorker:
    def __init__(
        self,
        config: OncallConfig,
        *,
        alert_source: AlertSource | None = None,
    ) -> None:
        self._config = config
        self._alert_source = alert_source or GrafanaAlertSource(
            base_url=config.grafana_url,
            token=config.grafana_token,
        )
        repo = Path(config.repo_path).resolve()
        state_path = repo / config.state_path
        self._cooldown = CooldownStore(
            state_path, cooldown_seconds=config.cooldown_seconds
        )
        self._session = ResponderSession(config)

    def process_once(self) -> list[str]:
        """Poll alerts and start at most one session per eligible fingerprint."""
        started: list[str] = []
        for alert in self._alert_source.list_firing():
            if not self._cooldown.should_start(alert.fingerprint):
                logger.info(
                    "skip fingerprint in cooldown",
                    extra={"fingerprint": alert.fingerprint},
                )
                continue
            self._cooldown.mark_started(alert.fingerprint)
            try:
                evidence = self._session.run(alert)
                started.append(evidence.branch_name)
                logger.info(
                    "session complete",
                    extra={"branch": evidence.branch_name},
                )
            finally:
                self._cooldown.mark_finished(alert.fingerprint)
        return started

    def run_forever(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        while True:
            self.process_once()
            time.sleep(self._config.poll_interval_seconds)


def main() -> None:
    config = OncallConfig.from_environ()
    OncallWorker(config).run_forever()


if __name__ == "__main__":
    main()
