# Test Constants:
from config.openai_config import GenaiEngineOpenAIProvider, OpenAISettings

DEFAULT_REGEX = ["\\d{3}-\\d{2}-\\d{4}", "\\d{5}-\\d{6}-\\d{7}"]
DEFAULT_KEYWORDS = ["key_word_1", "key_word_2"]
DEFAULT_EXAMPLES = [{"example": "John has O negative blood group", "result": True}]
EXAMPLE_RESPONSES = [
    # Space facts!
    'The Milky Way, our home galaxy, is estimated to contain over 100 billion stars and is just one of billions of galaxies in the observable universe. Astronomers use a unit of measurement called a "light-year" to describe vast cosmic distances, which is the distance that light travels in one year, roughly 5.88 trillion miles (9.46 trillion kilometers). Black holes are incredibly dense regions in space where gravity is so strong that nothing, not even light, can escape their grasp, making them invisible to direct observation. The study of cosmic microwave background radiation, leftover from the Big Bang, provides crucial evidence supporting the Big Bang theory as the origin of the universe. Exoplanets are planets located outside our solar system, and thousands have been discovered to date, sparking interest in the search for extraterrestrial life.',
]

EXAMPLE_PROMPTS = [
    # Space facts!
    "Tell me some fun facts about space. Avoid anything about aliens.",
]

DEFAULT_AZURE_OPENAI_SETTINGS = OpenAISettings(
    GENAI_ENGINE_OPENAI_PROVIDER=GenaiEngineOpenAIProvider.AZURE,
    GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS=60,
    GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD=60,
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS="model-gpt-azure::dummy_gpt_url/::dummy_api_key",
    GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS="model-embeddings-azure::dummy_embeddings_url/::dummy_api_key",
)
DEFAULT_VANILLA_OPENAI_SETTINGS = OpenAISettings(
    GENAI_ENGINE_OPENAI_PROVIDER=GenaiEngineOpenAIProvider.OPENAI,
    GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS=60,
    GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD=60,
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS="model-gpt-vanilla::dummy_gpt_url/::dummy_api_key",
    GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS="model-embeddings-vanilla::dummy_embeddings_url/::dummy_api_key",
)
