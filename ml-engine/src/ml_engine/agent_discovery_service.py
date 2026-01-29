"""Periodic agent discovery service - runs in background."""
import logging
import time
from threading import Thread
from typing import Any

import requests
from arthur_client.api_bindings import ApiClient, UnregisteredAgentsV1Api
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentDiscoveryService:
    """Periodically discovers agents and stores them in app-plane."""

    AGENT_DISCOVERY_HOST = "http://agent-discovery-service:8000"
    AGENT_DISCOVERY_TIMEOUT = 120
    DISCOVERY_INTERVAL_SECONDS = 300  # Run every 5 minutes

    def __init__(self) -> None:
        """Initialize the agent discovery service."""
        ssl_verify = Config.get_bool("KEYCLOAK_SSL_VERIFY", True)
        sess = ArthurClientCredentialsAPISession(
            client_id=Config.settings.ARTHUR_CLIENT_ID,
            client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
            metadata=ArthurOIDCMetadata(
                arthur_host=Config.settings.ARTHUR_API_HOST,
                verify_ssl=ssl_verify,
            ),
            verify=ssl_verify,
        )
        client = ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(
                session=sess,
                verify_ssl=ssl_verify,
            ),
        )
        self.unregistered_agents_client = UnregisteredAgentsV1Api(client)
        self.running = False
        self.thread: Thread | None = None

    def discover_and_store_agents(self) -> None:
        """Discover agents and store them in all workspaces."""
        # TODO: This is hardcoded for now - will need to get actual workspace/dataplane IDs
        # For POC, we're using hardcoded values
        workspace_id = "956121fb-f316-4402-8dd1-dd259d0e535b"  # default workspace
        data_plane_id = "d775e380-a904-4604-ac44-8778977501f8"  # Arthur Data Plane

        logger.info("Starting agent discovery...")

        try:
            # Step 1: Call agent discovery service
            logger.info("Calling agent discovery service...")
            response = requests.post(
                f"{self.AGENT_DISCOVERY_HOST}/api/v1/vertex/agents",
                json={
                    "include_traces": True,
                    "trace_lookback_hours": None,  # Auto-calculate from 2026-01-01
                },
                timeout=self.AGENT_DISCOVERY_TIMEOUT,
            )
            response.raise_for_status()
            discovery_data = response.json()

            logger.info(f"Discovered {discovery_data.get('count', 0)} agents")

            # Step 2: Transform to app-plane format
            agents_to_store = []
            for agent in discovery_data.get("agents", []):
                # Map discovery response to PutUnregisteredAgents format
                agent_data = {
                    "name": agent.get("name", agent.get("agent_id")),
                    "data_plane_id": data_plane_id,
                    "infrastructure": agent.get("infrastructure", "GCP"),
                    "first_detected": agent.get("create_time"),
                    "num_spans": agent.get("num_spans", 0),
                    "tools": [{"name": tool} for tool in agent.get("tools", [])],
                    "sub_agents": [
                        {"name": subagent} for subagent in agent.get("subagents", [])
                    ],
                    # Use agent_id as creation source for deduplication
                    "creation_source": {"top_level_span_name": agent.get("agent_id")},
                }
                agents_to_store.append(agent_data)

            # Step 3: Store in app-plane using existing API
            if agents_to_store:
                logger.info(f"Storing {len(agents_to_store)} agents in app-plane...")
                self.unregistered_agents_client.put_unregistered_agents(
                    workspace_id=workspace_id,
                    put_unregistered_agents={"unregistered_agents": agents_to_store},
                )
                logger.info("Successfully stored agents")
            else:
                logger.info("No agents to store")

        except requests.RequestException as e:
            logger.error(f"Failed to call agent discovery service: {e}")
        except Exception as e:
            logger.error(f"Error during agent discovery: {e}", exc_info=True)

    def _run_loop(self) -> None:
        """Background thread that runs discovery periodically."""
        logger.info(
            f"Agent discovery service started - will run every {self.DISCOVERY_INTERVAL_SECONDS}s"
        )
        while self.running:
            try:
                self.discover_and_store_agents()
            except Exception as e:
                logger.error(f"Unexpected error in discovery loop: {e}", exc_info=True)

            # Sleep for the interval
            time.sleep(self.DISCOVERY_INTERVAL_SECONDS)

    def start(self) -> None:
        """Start the periodic discovery service in a background thread."""
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._run_loop, daemon=True, name="AgentDiscovery")
            self.thread.start()
            logger.info("Agent discovery service thread started")

    def stop(self) -> None:
        """Stop the periodic discovery service."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=10)
            logger.info("Agent discovery service stopped")
