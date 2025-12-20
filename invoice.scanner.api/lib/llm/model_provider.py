class BaseAdapter:
    async def stream_chat(self, prompt):
        raise NotImplementedError

import config

class OpenAIAdapter(BaseAdapter):
    async def stream_chat(self, prompt):
        import openai
        client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        stream = await client.chat.completions.create(
            model=config.OPENAI_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""


class AnthropicAdapter(BaseAdapter):
    async def stream_chat(self, prompt):
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        stream = await client.messages.create(
            model=config.ANTHROPIC_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for event in stream:
            if hasattr(event, "delta") and hasattr(event.delta, "text"):
                yield event.delta.text or ""

class GeminiAdapter(BaseAdapter):
    async def stream_chat(self, prompt):
        import google.generativeai as genai
        client = genai.GenerativeModel(model_name=config.GEMINI_MODEL_NAME)
        stream = client.generate_content(prompt, stream=True)
        async for chunk in stream:
            yield getattr(chunk, "text", getattr(chunk, "content", ""))

def get_model_adapter(model_name: str) -> BaseAdapter:
    """
    Factory to get the correct model adapter by name.
    Supported: 'openai', 'claude', 'gemini'
    """
    if model_name.lower() == "openai":
        return OpenAIAdapter()
    elif model_name.lower() == "claude":
        return AnthropicAdapter()
    elif model_name.lower() == "gemini":
        return GeminiAdapter()
    else:
        raise ValueError(f"Unknown model: {model_name}")