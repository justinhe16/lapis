"""Runtime configuration, read from the environment (.env optional).

Keys are all optional: Lapis degrades gracefully. No ANTHROPIC_API_KEY -> stage-1
only. No GITHUB_TOKEN -> gists uses the low unauthenticated rate limit. etc.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv() -> None:
    """Minimal .env loader (no dependency). Ignores if absent."""
    for path in (".env", os.path.join(os.path.dirname(__file__), "..", ".env")):
        if os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


_load_dotenv()


@dataclass(frozen=True)
class Config:
    # acquisition
    active: bool = os.environ.get("LAPIS_ACTIVE", "0") == "1"   # allow read-only live polling
    rate_per_host: float = float(os.environ.get("LAPIS_RATE_PER_HOST", "1.0"))  # req/sec/host
    # Identify yourself politely. Set LAPIS_UA in .env to add a contact address.
    user_agent: str = os.environ.get(
        "LAPIS_UA", "LapisResearch/0.1 (agent-coordination study; +set LAPIS_UA for contact)")
    data_dir: str = os.environ.get("LAPIS_DATA_DIR", "data")

    # classifier (stage 2). Stage-1 heuristics already do the cheap filtering, so
    # stage-2 is a single confirm call. Sonnet by default — good enough for the
    # verdict and cheaper for volume; override with LAPIS_MODEL (e.g. claude-opus-5).
    anthropic_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    model_confirm: str = os.environ.get("LAPIS_MODEL", "claude-sonnet-5")

    # per-source creds
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    etherscan_key: str = os.environ.get("ETHERSCAN_API_KEY", "")
    eth_rpc: str = os.environ.get("ETH_RPC_URL", "")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_key)


CONFIG = Config()
