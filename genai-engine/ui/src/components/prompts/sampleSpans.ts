import { SpanWithMetricsResponse } from "@/lib/api-client/api-client";

// Sample spans representing real-world usage patterns
export const sampleSpans: SpanWithMetricsResponse[] = [
  // Sample 1: Simple LLM conversation without tools (LiteLLM format)
  {
    id: "span-001",
    trace_id: "trace-weather-001",
    span_id: "span-llm-001",
    parent_span_id: null,
    span_kind: "LLM",
    span_name: "litellm-acompletion",
    start_time: "2024-01-15T10:30:00Z",
    end_time: "2024-01-15T10:30:02Z",
    created_at: "2024-01-15T10:30:02Z",
    updated_at: "2024-01-15T10:30:02Z",
    status_code: "Ok",
    task_id: "task-weather-assistant",
    session_id: "session-user-123",
    system_prompt: "You are a helpful weather assistant. Provide accurate and friendly weather information.",
    user_query: "What's the weather like in San Francisco today?",
    response: "I don't have access to real-time weather data, but I can help you find weather information. You can check your local weather app or visit weather.com for current conditions in San Francisco.",
    context: [
      {
        role: "system",
        content: "You are a helpful weather assistant. Provide accurate and friendly weather information."
      },
      {
        role: "user", 
        content: "What's the weather like in San Francisco today?"
      },
      {
        role: "assistant",
        content: "I don't have access to real-time weather data, but I can help you find weather information. You can check your local weather app or visit weather.com for current conditions in San Francisco."
      }
    ],
    raw_data: {
      name: "litellm-acompletion",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a3",
        span_id: "0xd8d3476a2eb12724",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: null,
      start_time: "2024-01-15T10:30:00Z",
      end_time: "2024-01-15T10:30:02Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "LLM",
        "llm.model_name": "gpt-4",
        "llm.token_count.prompt": 45,
        "llm.token_count.completion": 67,
        "llm.token_count.total": 112,
        "llm.input_messages.0.message.role": "system",
        "llm.input_messages.0.message.content": "You are a helpful weather assistant. Provide accurate and friendly weather information.",
        "llm.input_messages.1.message.role": "user",
        "llm.input_messages.1.message.content": "What's the weather like in San Francisco today?",
        "llm.output_messages.0.message.role": "assistant",
        "llm.output_messages.0.message.content": "I don't have access to real-time weather data, but I can help you find weather information. You can check your local weather app or visit weather.com for current conditions in San Francisco.",
        "session.id": "session-user-123",
        "litellm.model": "gpt-4",
        "litellm.provider": "openai",
        "litellm.api_base": "https://api.openai.com/v1",
        "litellm.stream": false,
        "litellm.max_tokens": 1000,
        "litellm.temperature": 0.7,
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "gpt-4", "ls_model_type": "chat", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-001",
        metric_id: "query-relevance-metric",
        metric_type: "QueryRelevance",
        span_id: "span-001",
        prompt_tokens: 45,
        completion_tokens: 67,
        latency_ms: 1850,
        details: '{"query_relevance": {"llm_relevance_score": 0.89}, "reason": "Query is highly relevant to weather assistance task"}',
        created_at: "2024-01-15T10:30:02Z",
        updated_at: "2024-01-15T10:30:02Z"
      }
    ]
  },

  // Sample 2: LLM with tool calls for weather API (LiteLLM format)
  {
    id: "span-002",
    trace_id: "trace-weather-002",
    span_id: "span-llm-002",
    parent_span_id: null,
    span_kind: "LLM",
    span_name: "litellm-acompletion",
    start_time: "2024-01-15T11:15:00Z",
    end_time: "2024-01-15T11:15:04Z",
    created_at: "2024-01-15T11:15:04Z",
    updated_at: "2024-01-15T11:15:04Z",
    status_code: "Ok",
    task_id: "task-weather-assistant",
    session_id: "session-user-456",
    system_prompt: "You are a helpful weather assistant with access to real-time weather data. Use the get_weather tool to fetch current conditions.",
    user_query: "What's the current temperature in New York?",
    response: "The current temperature in New York is 22°C (72°F) with partly cloudy conditions and 68% humidity.",
    context: [
      {
        role: "system",
        content: "You are a helpful weather assistant with access to real-time weather data. Use the get_weather tool to fetch current conditions."
      },
      {
        role: "user",
        content: "What's the current temperature in New York?"
      },
      {
        role: "assistant",
        content: "I'll check the current weather in New York for you.",
        tool_calls: [
          {
            id: "call_weather_nyc_001",
            type: "function",
            function: {
              name: "get_weather",
              arguments: '{"location": "New York", "units": "celsius"}'
            }
          }
        ]
      },
      {
        role: "tool",
        name: "get_weather",
        content: '{"temperature": 22, "condition": "Partly cloudy", "humidity": 68, "location": "New York"}',
        tool_call_id: "call_weather_nyc_001"
      },
      {
        role: "assistant",
        content: "The current temperature in New York is 22°C (72°F) with partly cloudy conditions and 68% humidity."
      }
    ],
    raw_data: {
      name: "litellm-acompletion",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a4",
        span_id: "0xd8d3476a2eb12725",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: null,
      start_time: "2024-01-15T11:15:00Z",
      end_time: "2024-01-15T11:15:04Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "LLM",
        "llm.model_name": "gpt-4",
        "llm.token_count.prompt": 89,
        "llm.token_count.completion": 52,
        "llm.token_count.total": 141,
        "llm.input_messages.0.message.role": "system",
        "llm.input_messages.0.message.content": "You are a helpful weather assistant with access to real-time weather data. Use the get_weather tool to fetch current conditions.",
        "llm.input_messages.1.message.role": "user",
        "llm.input_messages.1.message.content": "What's the current temperature in New York?",
        "llm.input_messages.2.message.role": "assistant",
        "llm.input_messages.2.message.content": "I'll check the current weather in New York for you.",
        "llm.input_messages.2.message.tool_calls.0.tool_call.function.name": "get_weather",
        "llm.input_messages.2.message.tool_calls.0.tool_call.function.arguments": '{"location": "New York", "units": "celsius"}',
        "llm.input_messages.2.message.tool_calls.0.tool_call.id": "call_weather_nyc_001",
        "llm.input_messages.3.message.role": "tool",
        "llm.input_messages.3.message.name": "get_weather",
        "llm.input_messages.3.message.content": '{"temperature": 22, "condition": "Partly cloudy", "humidity": 68, "location": "New York"}',
        "llm.input_messages.3.message.tool_call_id": "call_weather_nyc_001",
        "llm.input_messages.4.message.role": "assistant",
        "llm.input_messages.4.message.content": "The current temperature in New York is 22°C (72°F) with partly cloudy conditions and 68% humidity.",
        "session.id": "session-user-456",
        "litellm.model": "gpt-4",
        "litellm.provider": "openai",
        "litellm.api_base": "https://api.openai.com/v1",
        "litellm.stream": false,
        "litellm.max_tokens": 1000,
        "litellm.temperature": 0.7,
        "litellm.tools": '[{"type": "function", "function": {"name": "get_weather", "description": "Get current weather information for a location", "parameters": {"type": "object", "properties": {"location": {"type": "string"}, "units": {"type": "string"}}, "required": ["location"]}}]',
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "gpt-4", "ls_model_type": "chat", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-002",
        metric_id: "query-relevance-metric",
        metric_type: "QueryRelevance",
        span_id: "span-002",
        prompt_tokens: 89,
        completion_tokens: 52,
        latency_ms: 3200,
        details: '{"query_relevance": {"llm_relevance_score": 0.95}, "reason": "Query is highly relevant and tool was used correctly"}',
        created_at: "2024-01-15T11:15:04Z",
        updated_at: "2024-01-15T11:15:04Z"
      },
      {
        id: "metric-003",
        metric_id: "tool-selection-metric",
        metric_type: "ToolSelection",
        span_id: "span-002",
        prompt_tokens: 89,
        completion_tokens: 52,
        latency_ms: 3200,
        details: '{"tool_selection": {"tool_selection": 1, "tool_usage": 1, "tool_selection_reason": "Correct weather tool was selected", "tool_usage_reason": "Tool was used correctly with proper parameters"}}',
        created_at: "2024-01-15T11:15:04Z",
        updated_at: "2024-01-15T11:15:04Z"
      }
    ]
  },

  // Sample 3: Tool execution span (LiteLLM format)
  {
    id: "span-003",
    trace_id: "trace-weather-002",
    span_id: "span-tool-001",
    parent_span_id: "span-llm-002",
    span_kind: "TOOL",
    span_name: "litellm-tool-call",
    start_time: "2024-01-15T11:15:01Z",
    end_time: "2024-01-15T11:15:02Z",
    created_at: "2024-01-15T11:15:02Z",
    updated_at: "2024-01-15T11:15:02Z",
    status_code: "Ok",
    task_id: "task-weather-assistant",
    session_id: "session-user-456",
    system_prompt: null,
    user_query: null,
    response: '{"temperature": 22, "condition": "Partly cloudy", "humidity": 68, "location": "New York"}',
    context: [
      {
        role: "tool",
        name: "get_weather",
        content: '{"temperature": 22, "condition": "Partly cloudy", "humidity": 68, "location": "New York"}'
      }
    ],
    raw_data: {
      name: "litellm-tool-call",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a4",
        span_id: "0xd8d3476a2eb12726",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: "0xd8d3476a2eb12725",
      start_time: "2024-01-15T11:15:01Z",
      end_time: "2024-01-15T11:15:02Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "TOOL",
        "tool.name": "get_weather",
        "tool.description": "Get current weather information for a location",
        "tool.success": true,
        "tool.input": '{"location": "New York", "units": "celsius"}',
        "tool.output": '{"temperature": 22, "condition": "Partly cloudy", "humidity": 68, "location": "New York"}',
        "session.id": "session-user-456",
        "litellm.tool_name": "get_weather",
        "litellm.tool_call_id": "call_weather_nyc_001",
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "weather_api", "ls_model_type": "tool", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: []
  },

  // Sample 4: Agent span with multiple tool calls (LiteLLM format)
  {
    id: "span-004",
    trace_id: "trace-agent-001",
    span_id: "span-agent-001",
    parent_span_id: null,
    span_kind: "AGENT",
    span_name: "litellm-agent",
    start_time: "2024-01-15T14:20:00Z",
    end_time: "2024-01-15T14:20:08Z",
    created_at: "2024-01-15T14:20:08Z",
    updated_at: "2024-01-15T14:20:08Z",
    status_code: "Ok",
    task_id: "task-travel-planner",
    session_id: "session-user-789",
    system_prompt: "You are a travel planning agent. Help users plan trips by checking weather, finding flights, and booking hotels.",
    user_query: "I want to plan a trip to Paris next week. Can you help me with weather and flight information?",
    response: "I'll help you plan your trip to Paris! Let me check the weather forecast and find some flight options for you.",
    context: [
      {
        role: "system",
        content: "You are a travel planning agent. Help users plan trips by checking weather, finding flights, and booking hotels."
      },
      {
        role: "user",
        content: "I want to plan a trip to Paris next week. Can you help me with weather and flight information?"
      },
      {
        role: "assistant",
        content: "I'll help you plan your trip to Paris! Let me check the weather forecast and find some flight options for you.",
        tool_calls: [
          {
            id: "call_weather_paris_001",
            type: "function",
            function: {
              name: "get_weather_forecast",
              arguments: '{"location": "Paris", "days": 7}'
            }
          },
          {
            id: "call_flights_001",
            type: "function", 
            function: {
              name: "search_flights",
              arguments: '{"destination": "Paris", "departure_date": "2024-01-22", "return_date": "2024-01-29"}'
            }
          }
        ]
      }
    ],
    raw_data: {
      name: "litellm-agent",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a5",
        span_id: "0xd8d3476a2eb12727",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: null,
      start_time: "2024-01-15T14:20:00Z",
      end_time: "2024-01-15T14:20:08Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "AGENT",
        "agent.name": "WeatherAgent",
        "agent.version": "1.0.0",
        "agent.tools": '["get_weather_forecast", "search_flights"]',
        "session.id": "session-user-789",
        "litellm.agent_name": "WeatherAgent",
        "litellm.agent_type": "travel_planner",
        "litellm.model": "gpt-4",
        "litellm.provider": "openai",
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "agent_model", "ls_model_type": "agent", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-004",
        metric_id: "agent-effectiveness-metric",
        metric_type: "ResponseRelevance",
        span_id: "span-004",
        prompt_tokens: 156,
        completion_tokens: 78,
        latency_ms: 7500,
        details: '{"agent_effectiveness": {"task_completion": 0.85, "tool_usage_efficiency": 0.92}, "reason": "Agent successfully initiated multiple tool calls for comprehensive trip planning"}',
        created_at: "2024-01-15T14:20:08Z",
        updated_at: "2024-01-15T14:20:08Z"
      }
    ]
  },

  // Sample 5: RAG retrieval span (LiteLLM format)
  {
    id: "span-005",
    trace_id: "trace-rag-001",
    span_id: "span-retriever-001",
    parent_span_id: "span-agent-001",
    span_kind: "RETRIEVER",
    span_name: "litellm-retriever",
    start_time: "2024-01-15T14:20:02Z",
    end_time: "2024-01-15T14:20:03Z",
    created_at: "2024-01-15T14:20:03Z",
    updated_at: "2024-01-15T14:20:03Z",
    status_code: "Ok",
    task_id: "task-travel-planner",
    session_id: "session-user-789",
    system_prompt: null,
    user_query: "Paris travel guide recommendations",
    response: '{"documents": [{"title": "Paris Travel Guide", "content": "Paris is known for its art, culture, and cuisine...", "score": 0.95}], "total_results": 5}',
    context: [
      {
        role: "retriever",
        content: "Retrieved 5 relevant documents about Paris travel"
      }
    ],
    raw_data: {
      name: "litellm-retriever",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a6",
        span_id: "0xd8d3476a2eb12728",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: "0xd8d3476a2eb12727",
      start_time: "2024-01-15T14:20:02Z",
      end_time: "2024-01-15T14:20:03Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "RETRIEVER",
        "retrieval.query": "Paris travel guide recommendations",
        "retrieval.documents": 5,
        "retrieval.top_k": 5,
        "retrieval.scores": '[0.95, 0.89, 0.87, 0.85, 0.82]',
        "session.id": "session-user-789",
        "litellm.retriever_type": "vector_search",
        "litellm.embedding_model": "text-embedding-ada-002",
        "litellm.vector_store": "pinecone",
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "retriever_model", "ls_model_type": "retriever", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-005",
        metric_id: "retrieval-relevance-metric",
        metric_type: "QueryRelevance",
        span_id: "span-005",
        prompt_tokens: 0,
        completion_tokens: 0,
        latency_ms: 1200,
        details: '{"retrieval_relevance": {"average_score": 0.89, "top_score": 0.95}, "reason": "Retrieved documents are highly relevant to Paris travel query"}',
        created_at: "2024-01-15T14:20:03Z",
        updated_at: "2024-01-15T14:20:03Z"
      }
    ]
  },

  // Sample 6: Error span (LiteLLM format)
  {
    id: "span-006",
    trace_id: "trace-error-001",
    span_id: "span-error-001",
    parent_span_id: null,
    span_kind: "LLM",
    span_name: "litellm-acompletion",
    start_time: "2024-01-15T16:45:00Z",
    end_time: "2024-01-15T16:45:01Z",
    created_at: "2024-01-15T16:45:01Z",
    updated_at: "2024-01-15T16:45:01Z",
    status_code: "Error",
    task_id: "task-error-handling",
    session_id: "session-user-error",
    system_prompt: "You are a helpful assistant.",
    user_query: "Generate a very long response that exceeds token limits",
    response: null,
    context: [
      {
        role: "system",
        content: "You are a helpful assistant."
      },
      {
        role: "user",
        content: "Generate a very long response that exceeds token limits"
      }
    ],
    raw_data: {
      name: "litellm-acompletion",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a7",
        span_id: "0xd8d3476a2eb12729",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: null,
      start_time: "2024-01-15T16:45:00Z",
      end_time: "2024-01-15T16:45:01Z",
      status: {
        status_code: "ERROR"
      },
      attributes: {
        "openinference.span.kind": "LLM",
        "llm.model_name": "gpt-4",
        "error.message": "Token limit exceeded",
        "error.type": "TokenLimitExceeded",
        "error.code": "context_length_exceeded",
        "session.id": "session-user-error",
        "litellm.model": "gpt-4",
        "litellm.provider": "openai",
        "litellm.error": "Token limit exceeded",
        "litellm.error_type": "TokenLimitExceeded",
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "gpt-4", "ls_model_type": "chat", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-006",
        metric_id: "error-rate-metric",
        metric_type: "ResponseRelevance",
        span_id: "span-006",
        prompt_tokens: 25,
        completion_tokens: 0,
        latency_ms: 500,
        details: '{"error_rate": {"has_error": true, "error_type": "TokenLimitExceeded"}, "reason": "Request failed due to token limit exceeded"}',
        created_at: "2024-01-15T16:45:01Z",
        updated_at: "2024-01-15T16:45:01Z"
      }
    ]
  },

  // Sample 7: Chain span (LiteLLM format)
  {
    id: "span-007",
    trace_id: "trace-chain-001",
    span_id: "span-chain-001",
    parent_span_id: null,
    span_kind: "CHAIN",
    span_name: "litellm-chain",
    start_time: "2024-01-15T18:30:00Z",
    end_time: "2024-01-15T18:30:05Z",
    created_at: "2024-01-15T18:30:05Z",
    updated_at: "2024-01-15T18:30:05Z",
    status_code: "Ok",
    task_id: "task-weather-chain",
    session_id: "session-user-chain",
    system_prompt: null,
    user_query: "Get weather for multiple cities: London, Tokyo, Sydney",
    response: "Weather data retrieved for London, Tokyo, and Sydney",
    context: [
      {
        role: "chain",
        content: "Executed weather retrieval chain for multiple cities"
      }
    ],
    raw_data: {
      name: "litellm-chain",
      context: {
        trace_id: "0x8d354e2346060032703637a0843b20a8",
        span_id: "0xd8d3476a2eb12730",
        trace_state: "[]"
      },
      kind: "SpanKind.INTERNAL",
      parent_id: null,
      start_time: "2024-01-15T18:30:00Z",
      end_time: "2024-01-15T18:30:05Z",
      status: {
        status_code: "OK"
      },
      attributes: {
        "openinference.span.kind": "CHAIN",
        "chain.name": "WeatherChain",
        "chain.input": "Get weather for multiple cities: London, Tokyo, Sydney",
        "chain.output": "Weather data retrieved for London, Tokyo, and Sydney",
        "chain.steps": 3,
        "session.id": "session-user-chain",
        "litellm.chain_name": "WeatherChain",
        "litellm.chain_type": "parallel_execution",
        "litellm.models": '["gpt-4", "gpt-4", "gpt-4"]',
        "litellm.providers": '["openai", "openai", "openai"]',
        "metadata": '{"ls_provider": "litellm", "ls_model_name": "chain_model", "ls_model_type": "chain", "litellm_version": "1.0.0"}'
      },
      events: [],
      links: [],
      resource: {
        attributes: {
          "service.name": "litellm",
          "service.version": "1.0.0"
        },
        schema_url: ""
      },
      arthur_span_version: "arthur_span_v1"
    },
    metric_results: [
      {
        id: "metric-007",
        metric_id: "chain-efficiency-metric",
        metric_type: "QueryRelevance",
        span_id: "span-007",
        prompt_tokens: 0,
        completion_tokens: 0,
        latency_ms: 4800,
        details: '{"chain_efficiency": {"execution_time": 4800, "success_rate": 1.0}, "reason": "Chain executed successfully for all cities"}',
        created_at: "2024-01-15T18:30:05Z",
        updated_at: "2024-01-15T18:30:05Z"
      }
    ]
  }
];

// Export individual spans for easy access
export const simpleLLMSpan = sampleSpans[0];
export const toolCallSpan = sampleSpans[1];
export const toolExecutionSpan = sampleSpans[2];
export const agentSpan = sampleSpans[3];
export const ragRetrievalSpan = sampleSpans[4];
export const errorSpan = sampleSpans[5];
export const chainSpan = sampleSpans[6];
