"""Worker Lifecycle Manager for Sovereign Intelligence.

Manages background workers (market data feed, currency converter, alert engine, trading bot).
Enforces single-instance execution via cross-platform file locking to prevent duplicate
background threads across multiple WSGI worker processes or auto-reloading servers.
Provides health tracking, error logging, and graceful shutdown.
"""

import atexit
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("stock_sense.worker_manager")

# Platform-specific locking
try:
    import msvcrt
    IS_WINDOWS = True
except ImportError:
    import fcntl
    IS_WINDOWS = False


class ProcessLock:
    """Cross-platform advisory file lock."""

    def __init__(self, lock_file_path: Path):
        self.lock_file_path = lock_file_path
        self._fd = None
        self.acquired = False

    def acquire(self) -> bool:
        """Attempt to acquire non-blocking lock. Return True if acquired, False otherwise."""
        try:
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = open(self.lock_file_path, "w+")

            if IS_WINDOWS:
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            self.acquired = True
            # Write current PID into lock file for inspection
            self._fd.seek(0)
            self._fd.truncate()
            self._fd.write(f"pid={os.getpid()}\ntime={datetime.now(timezone.utc).isoformat()}\n")
            self._fd.flush()
            return True
        except (IOError, OSError, BlockingIOError):
            self.acquired = False
            if self._fd:
                try:
                    self._fd.close()
                except Exception:
                    pass
                self._fd = None
            return False

    def release(self) -> None:
        """Release the file lock."""
        if not self.acquired or not self._fd:
            return
        try:
            if IS_WINDOWS:
                self._fd.seek(0)
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.debug(f"Error unlocking file: {e}")
        finally:
            try:
                self._fd.close()
            except Exception:
                pass
            self._fd = None
            self.acquired = False


class WorkerManager:
    """Coordinates startup, monitoring, single-instance locking, and shutdown of background workers."""

    def __init__(self):
        self.lock = None
        self.is_leader = False
        self._stop_requested = threading.Event()
        self._workers_started = False
        self._threads: Dict[str, threading.Thread] = {}
        self._health: Dict[str, Dict[str, Any]] = {
            "market_data_feed": {"status": "stopped", "last_heartbeat": None, "last_error": None},
            "currency_converter": {"status": "stopped", "last_heartbeat": None, "last_error": None},
            "alert_engine": {"status": "stopped", "last_heartbeat": None, "last_error": None},
            "trading_bot": {"status": "stopped", "last_heartbeat": None, "last_error": None},
        }
        self._state_lock = threading.Lock()

        # Register cleanup on process exit
        atexit.register(self.stop_all)

    def is_running(self, name: str) -> bool:
        with self._state_lock:
            info = self._health.get(name, {})
            return info.get("status") == "running"

    def record_heartbeat(self, name: str) -> None:
        with self._state_lock:
            if name in self._health:
                self._health[name]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                self._health[name]["status"] = "running"

    def record_error(self, name: str, error_message: str) -> None:
        with self._state_lock:
            if name in self._health:
                self._health[name]["status"] = "error"
                self._health[name]["last_error"] = error_message
                self._health[name]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        logger.error(f"[Worker:{name}] Failure reported: {error_message}")

    def get_health_status(self) -> Dict[str, Any]:
        """Return snapshot of worker states."""
        with self._state_lock:
            return {
                "is_leader": self.is_leader,
                "workers_started": self._workers_started,
                "workers": {k: dict(v) for k, v in self._health.items()}
            }

    def start_all(self, app=None, lock_path: Optional[Path] = None) -> bool:
        """
        Attempt to acquire single-instance lock and start background worker threads.
        Returns True if this process acquired leadership and started workers, False otherwise.
        """
        if self._workers_started:
            return self.is_leader

        # Check explicit environment flag
        env_enable = os.getenv("ENABLE_BACKGROUND_WORKERS", "true").lower()
        if env_enable not in ("true", "1", "yes"):
            logger.info("Background workers explicitly disabled via ENABLE_BACKGROUND_WORKERS=false")
            return False

        # In testing mode, default to not starting background loops unless forced
        if app and app.config.get("TESTING"):
            logger.info("Application is in TESTING mode; skipping background worker startup.")
            return False

        if lock_path is None:
            from config import Config
            lock_path = Path(Config.BASE_DIR) / "data" / "workers.lock"

        self.lock = ProcessLock(lock_path)
        if not self.lock.acquire():
            logger.info(
                f"[WorkerManager] PID {os.getpid()} could not acquire worker lock. "
                f"Another process is active leader. Running in API-only mode."
            )
            self.is_leader = False
            return False

        self.is_leader = True
        self._workers_started = True
        self._stop_requested.clear()
        logger.info(f"[WorkerManager] PID {os.getpid()} acquired leader lock. Starting background workers...")

        # 1. Market Data Feed
        self._start_supervised_worker("market_data_feed", self._run_market_data_feed)

        # 2. Currency Converter
        self._start_supervised_worker("currency_converter", self._run_currency_converter)

        # 3. Alert Engine
        self._start_supervised_worker("alert_engine", self._run_alert_engine)

        # 4. Trading Bot
        self._start_supervised_worker("trading_bot", self._run_trading_bot)

        return True

    def _start_supervised_worker(self, name: str, target: Callable) -> None:
        def supervised_target():
            with self._state_lock:
                self._health[name]["status"] = "running"
                self._health[name]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
            try:
                target()
            except Exception as e:
                self.record_error(name, str(e))
            finally:
                with self._state_lock:
                    if self._health[name]["status"] != "error":
                        self._health[name]["status"] = "stopped"

        t = threading.Thread(target=supervised_target, name=f"Worker-{name}", daemon=True)
        self._threads[name] = t
        t.start()
        logger.info(f"[WorkerManager] Started worker thread: {name}")

    def _run_market_data_feed(self) -> None:
        try:
            from market_data_feed import MarketDataFeed
            feed = MarketDataFeed(stock_interval=30, index_interval=60)
            feed.start()
            while not self._stop_requested.is_set():
                self.record_heartbeat("market_data_feed")
                time.sleep(10)
            feed.stop()
        except Exception as e:
            self.record_error("market_data_feed", str(e))

    def _run_currency_converter(self) -> None:
        try:
            from currency_converter import currency_converter
            # Perform initial update
            try:
                currency_converter.update_rates_from_api()
            except Exception as e:
                logger.warning(f"Initial currency update failed: {e}")

            while not self._stop_requested.is_set():
                self.record_heartbeat("currency_converter")
                # Sleep in short increments to allow rapid shutdown response
                for _ in range(360):
                    if self._stop_requested.is_set():
                        break
                    time.sleep(10)
                if not self._stop_requested.is_set():
                    try:
                        currency_converter.update_rates_from_api()
                    except Exception as e:
                        self.record_error("currency_converter", str(e))
        except Exception as e:
            self.record_error("currency_converter", str(e))

    def _run_alert_engine(self) -> None:
        try:
            from alert_engine import alert_engine
            alert_engine.start()
            while not self._stop_requested.is_set():
                self.record_heartbeat("alert_engine")
                time.sleep(15)
            alert_engine.stop()
        except Exception as e:
            self.record_error("alert_engine", str(e))

    def _run_trading_bot(self) -> None:
        try:
            import trading_bot.main as bot
            bot.init_trading_system()
            # Bot engine main loop checks market hours and scans
            bot.run_bot_engine()
        except Exception as e:
            self.record_error("trading_bot", str(e))

    def stop_all(self) -> None:
        """Signal all workers to stop and release lock."""
        if not self._workers_started:
            return

        logger.info("[WorkerManager] Stopping all background workers...")
        self._stop_requested.set()

        with self._state_lock:
            for name in self._health:
                if self._health[name]["status"] == "running":
                    self._health[name]["status"] = "stopped"

        if self.lock and self.lock.acquired:
            self.lock.release()
            logger.info("[WorkerManager] Leader lock released.")

        self._workers_started = False
        self.is_leader = False


# Global singleton manager
worker_manager = WorkerManager()
