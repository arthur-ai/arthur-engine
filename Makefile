.PHONY: help start stop restart down

help:
	@echo "Usage: make [command]"
	@echo "Commands:"
	@echo "  help    Show this help"
	@echo "  start   Start the services"
	@echo "  setup-env-file   Setup the .env file"
	@echo "  stop    Stop the services"
	@echo "  restart   Restart the services"
	@echo "  down    Down the services\n"
	@echo "Service specific commands:"
	@echo "  genai-engine:"
	@echo "    start-genai-engine   Start the genai-engine service"
	@echo "    stop-genai-engine   Stop the genai-engine service"
	@echo "    restart-genai-engine   Restart the genai-engine service"
	@echo "    down-genai-engine   Down the genai-engine service\n"
	@echo "  ml-engine:"
	@echo "    start-ml-engine   Start the ml-engine service"
	@echo "    stop-ml-engine   Stop the ml-engine service"
	@echo "    restart-ml-engine   Restart the ml-engine service"
	@echo "    down-ml-engine   Down the ml-engine service\n"

start: start-$(filter-out $@,$(MAKECMDGOALS))
	./docker-compose/start.sh

setup-env-file:
	./docker-compose/setup_env_file.sh ./docker-compose/.env

stop: stop-$(filter-out $@,$(MAKECMDGOALS))
	docker compose -f docker-compose/docker-compose.yml stop

restart: restart-$(filter-out $@,$(MAKECMDGOALS))
	docker compose -f docker-compose/docker-compose.yml restart

down: down-$(filter-out $@,$(MAKECMDGOALS))
	docker compose -f docker-compose/docker-compose.yml down

# Start commands
start-genai-engine:
	docker compose -f docker-compose/docker-compose.yml up db genai-engine -d

start-ml-engine:
	docker compose -f docker-compose/docker-compose.yml up ml-engine -d

# Stop commands
stop-genai-engine:
	docker compose -f docker-compose/docker-compose.yml stop db genai-engine

stop-ml-engine:
	docker compose -f docker-compose/docker-compose.yml stop ml-engine

# Restart commands
restart-genai-engine:
	docker compose -f docker-compose/docker-compose.yml restart db genai-engine

restart-ml-engine:
	docker compose -f docker-compose/docker-compose.yml restart ml-engine

# Down commands
down-genai-engine:
	docker compose -f docker-compose/docker-compose.yml down db genai-engine

down-ml-engine:
	docker compose -f docker-compose/docker-compose.yml down ml-engine

%:
	@true
