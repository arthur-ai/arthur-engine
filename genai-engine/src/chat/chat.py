import logging
import re
from typing import List

from arthur_common.models.enums import PaginationSortMethod
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from opentelemetry import trace

from repositories.embedding_repository import EmbeddingRepository
from repositories.inference_repository import InferenceRepository
from schemas.internal_schemas import AugmentedRetrieval
from scorer.llm_client import get_llm_executor
from utils import constants
from utils.token_count import TokenCounter

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()


class ArthurChat:
    MAX_HISTORY_CONTEXT: int = constants.MAX_CHAT_HISTORY_CONTEXT
    MAX_CONTEXT_LIMIT: int = constants.MAX_CHAT_CONTEXT_LIMIT

    def _sanitize_text(self, text: str) -> str:
        """Replaces single curly braces with double curly braces, as single brackets are treated as placeholders by LangChain

        :param text: text to clean
        """
        return re.sub(r"(?<!})}(?!})", "}}", re.sub(r"(?<!{){(?!{)", "{{", text))

    def __init__(
        self,
        inference_repository: InferenceRepository,
        embeddings_repository: EmbeddingRepository,
        conversation_id: str,
        file_ids: List[str],
    ):
        """Initializes Arthur Chat object

        :param inference_repository: class to query inference table
        :param embeddings_repository: class to query embeddings table
        :param conversation_id: conversation id
        :param file_ids: list of document ids
        """
        self.previous_message_history: List[BaseMessage] = []
        self.total_token_count: int = 0
        self.token_counter = TokenCounter()
        self.embedding_repository = embeddings_repository
        self.file_ids = file_ids
        self.retrieval_info = None

        # create the memory context
        self._create_memory_context(inference_repository, conversation_id)

    @tracer.start_as_current_span("create memory context")
    def _create_memory_context(
        self,
        inference_repository: InferenceRepository,
        conversation_id: str,
    ):
        """loads the template for the memory context with old inferences

        :param inference_repository: class to query inference table
        :param conversation_id: conversation id
        """

        inference_history, _ = inference_repository.query_inferences(
            sort=PaginationSortMethod.DESCENDING,
            conversation_id=conversation_id,
            page=0,
            page_size=50,
        )

        messages: List[BaseMessage] = [
            SystemMessage(content="Provided below are previous messages: "),
        ]

        self.total_token_count += self.token_counter.count(messages[0].content)
        index = 0
        total_count = 0

        while total_count < ArthurChat.MAX_HISTORY_CONTEXT and index < len(
            inference_history,
        ):
            inference = inference_history[index]

            inference_prompt, inference_response = None, None
            inference_prompt_token_count, inference_response_token_count = 0, 0

            if inference.inference_prompt:
                inference_prompt = f"Human Input: {self._sanitize_text(inference.inference_prompt.message)}"
                inference_prompt_token_count = self.token_counter.count(
                    inference_prompt,
                )

            if inference.inference_response:
                inference_response = f"LLM Response: {self._sanitize_text(inference.inference_response.message)}"
                inference_response_token_count = self.token_counter.count(
                    inference_response,
                )

            total_token_count = (
                total_count
                + inference_prompt_token_count
                + inference_response_token_count
            )

            if total_token_count < ArthurChat.MAX_HISTORY_CONTEXT:
                total_count = total_token_count
                if inference_prompt:
                    messages.append(HumanMessage(content=inference_prompt))

                if inference_response:
                    messages.append(AIMessage(content=inference_response))

            index += 1

        self.previous_message_history = messages

    @tracer.start_as_current_span("chat augmented context")
    def retrieve_augmented_context(
        self,
        query: str,
        limit: int = 3,
    ) -> AugmentedRetrieval:
        """loads in the context from the vector store"""
        embeddings = self.embedding_repository.get_embeddings(
            user_query=query,
            file_ids=self.file_ids,
            limit=limit,
        )
        embedding_messages = ["Provided below are reference documents: "]

        index = 0
        total_tokens = self.token_counter.count(embedding_messages[0])

        while total_tokens < ArthurChat.MAX_CONTEXT_LIMIT and index < len(embeddings):
            heading_str = f"""
            Reference Document {index}
            """
            context_str = f"""
            {embeddings[index].text}
            """
            retrieved_prompt_str = f"""
            {heading_str}
            {context_str}
            """
            prompt_tokens = self.token_counter.count(retrieved_prompt_str)
            if total_tokens + prompt_tokens > ArthurChat.MAX_CONTEXT_LIMIT:
                break

            total_tokens += prompt_tokens
            # prompt = SystemMessage(content=retrieved_prompt_str)
            embedding_messages.append(retrieved_prompt_str)

            index += 1
        retrieval_info = AugmentedRetrieval(
            messages=embedding_messages,
            embeddings=embeddings,
        )
        self.retrieval_info = retrieval_info
        self.total_token_count += total_tokens
        return retrieval_info

    @tracer.start_as_current_span("chat")
    def chat(self, user_query: str):
        """chat"""
        if not self.retrieval_info:
            self.retrieve_augmented_context(query=user_query)

        all_prompts = (
            self.previous_message_history
            + self.retrieval_info.messages
            + [HumanMessage(content=user_query)]
        )

        executor = get_llm_executor()
        chat_llm = executor.get_gpt_model(chat_temperature=0.0)
        call = lambda: chat_llm.invoke(all_prompts).content

        # Tokens used for chat not recorded
        output, _ = executor.execute(call, "chat response")

        return output
