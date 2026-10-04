from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from .models import MinimalSource

MODEL_NAME = "Qwen/Qwen3-0.6B"


def load_model() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    """Load the tokenizer and model once; reuse across every question."""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto")
    return tokenizer, model


def read_source_text(source: MinimalSource) -> str:
    """Re-read the exact chunk of text a source points to, from data/raw."""
    content = Path(source.file_path).read_text(encoding="utf-8")
    return content[source.first_character_index:source.last_character_index]


def build_context(sources: list[MinimalSource]) -> str:
    """Concatenate the retrieved chunks into one block of context text."""
    parts = []
    for source in sources:
        text = read_source_text(source)
        parts.append(f"From {source.file_path}:\n{text}")
    return "\n\n".join(parts)


def generate_answer(tokenizer: AutoTokenizer, model: AutoModelForCausalLM,
                    question: str, sources: list[MinimalSource],
                    max_new_tokens: int = 400) -> str:
    """Generate one grounded answer from the retrieved sources."""
    context = build_context(sources)
    system_message = ("You answer questions about the vLLM codebase using "
                      "only the context below. If the context does not "
                      "contain the answer, say so.\n\n" + context)
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,
    ).to(model.device)

    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()