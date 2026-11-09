import json
import logging
import sys
from pathlib import Path

from sweetline import clock, compose, corpus, deliver, state

ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("sweetline")


def setup_logging():
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def load_config(root):
    data = json.loads((Path(root) / "config.json").read_text(encoding="utf-8"))
    required = (
        "recipient",
        "timezone",
        "start_hour",
        "end_hour",
        "grace_minutes",
        "quote_cooldown_days",
        "frame_cooldown_days",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("missing " + ",".join(missing))
    return data


def run(argv=None, root=None, sender=None, moment=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in argv
    force = "--now" in argv
    root = ROOT if root is None else Path(root)
    setup_logging()
    try:
        config = load_config(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("%s", exc)
        return 1
    if moment is None:
        try:
            moment = clock.now(config["timezone"])
        except Exception as exc:
            logger.error("%s", exc)
            return 1
    slot = clock.slot_for(moment, config["start_hour"], config["end_hour"])
    if slot is None:
        return 0
    if not force and not clock.in_grace(moment, config["grace_minutes"]):
        return 0
    recipient = str(config.get("recipient", "")).strip()
    if not dry_run and not recipient:
        logger.error("missing recipient")
        return 1
    try:
        data = corpus.load(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("%s", exc)
        return 1
    sender = sender or deliver.send
    with state.locked(root):
        current = state.load_state(root)
        key = clock.hour_key(moment)
        if state.already_sent(current, key):
            return 0
        try:
            message, picks = compose.for_hour(
                data,
                slot,
                moment,
                current,
                config["quote_cooldown_days"],
                config["frame_cooldown_days"],
            )
        except ValueError as exc:
            logger.error("%s", exc)
            return 1
        if dry_run:
            print(message)
            return 0
        try:
            sender(recipient, message)
        except Exception as exc:
            logger.error("send failed: %s", exc)
            return 2
        state.record(root, key, picks, moment, config["quote_cooldown_days"])
    return 0
