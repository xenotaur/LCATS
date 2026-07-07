"""Library for chunking long stories into manageable pieces using tiktoken."""

from dataclasses import dataclass
from typing import List, Optional

import tiktoken


@dataclass
class Chunk:
    index: int  # sequential index of the chunk
    text: str  # text content of the chunk
    start_token: int  # index in tokenized list
    start_char: int  # index in original story string


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count the number of tokens in a text string for a given model using tiktoken."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def chunk_story(
    story_text: str,
    max_tokens: int = 6000,
    overlap_tokens: int = 0,
    model_name: str = "gpt-3.5-turbo",
    end_token_limit: Optional[int] = None,
    max_chunks: Optional[int] = None,
) -> List[Chunk]:
    """
    Token-aware chunking using tiktoken. Produces structured chunks with
    token and character offset metadata.

    Parameters:
    - max_tokens: number of tokens per chunk
    - overlap_tokens: tokens of overlap between consecutive chunks (0 disables overlap)
    - model_name: OpenAI model to use for encoding
    - end_token_limit: if set, truncate to this many tokens total
    - max_chunks: if set, return at most this many chunks
    """
    enc = tiktoken.encoding_for_model(model_name)
    tokens = enc.encode(story_text)

    if end_token_limit is not None:
        tokens = tokens[:end_token_limit]

    chunks: List[Chunk] = []
    current_token = 0
    chunk_count = 0

    step = max_tokens if overlap_tokens == 0 else max_tokens - overlap_tokens

    while current_token < len(tokens):
        if max_chunks is not None and chunk_count >= max_chunks:
            break

        # Calculate start and end tokens for the current chunk
        if chunks and overlap_tokens > 0:
            # If this is not the first chunk, start from the end of the last chunk minus overlap
            start_token = max(current_token - overlap_tokens, 0)
        else:
            # For the first chunk, start from the current token
            start_token = current_token
        end_token = min(current_token + max_tokens, len(tokens))
        chunk_tokens = tokens[start_token:end_token]
        chunk_text = enc.decode(chunk_tokens)
        start_char = len(enc.decode(tokens[:start_token]))

        chunks.append(
            Chunk(
                index=chunk_count,
                text=chunk_text,
                start_token=start_token,
                start_char=start_char,
            )
        )

        current_token += step
        chunk_count += 1

    return chunks


def summarize_chunks(chunks: List[Chunk]) -> str:
    """Return a string showing the first and last 100 characters of each chunk."""
    output_lines = []

    for index, chunk in enumerate(chunks):
        header = f"Chunk {index} ({len(chunk.text)} chars, starts at char {chunk.start_char}):"
        if len(chunk.text) > 200:
            snippet = chunk.text[:100] + " ... " + chunk.text[-100:]
        else:
            snippet = chunk.text
        output_lines.extend([header, snippet, ""])

    return "\n".join(output_lines)


def display_chunks(chunks: List[Chunk]) -> None:
    """Print a summary of each chunk to the console."""
    summary = summarize_chunks(chunks)
    print(summary)
    print(f"Total chunks: {len(chunks)}")
    print(f"Total characters: {sum(len(chunk.text) for chunk in chunks)}")
    print(f"Total tokens: {sum(count_tokens(chunk.text) for chunk in chunks)}")
