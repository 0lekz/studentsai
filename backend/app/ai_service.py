"""
AI service integration for StudentsAI MVP using OpenAI
"""

import asyncio
import logging
from typing import Any

import numpy as np
import openai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import OPENAI_API_KEY
from .schemas import GeneratedFlashcard

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)


class AIService:
    """AI service for text processing and generation"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    async def summarize_text(self, content: str) -> str:
        """Generate summary of text content"""
        try:
            prompt = f"""
            Please provide a concise summary of the following text. 
            Focus on the key points and main ideas. 
            Keep the summary clear and well-structured.
            
            Text to summarize:
            {content}
            
            Summary:
            """

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates clear, concise summaries of academic and educational content.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            return summary

        except Exception as e:
            logger.error(f"Error in summarize_text: {e!s}")
            raise Exception(f"Failed to generate summary: {e!s}") from e

    async def generate_flashcards(
        self, content: str, count: int = 5
    ) -> list[GeneratedFlashcard]:
        """Generate flashcards from text content"""
        try:
            prompt = f"""
            Create {count} educational flashcards from the following content.
            Each flashcard should have a clear question and a concise answer.
            Focus on key concepts, definitions, and important facts.
            Format your response as a JSON array with objects containing "question" and "answer" fields.
            
            Content:
            {content}
            
            Generate exactly {count} flashcards in this JSON format:
            [
                {{"question": "What is...", "answer": "..."}},
                {{"question": "How does...", "answer": "..."}},
                ...
            ]
            """

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational assistant that creates high-quality study flashcards. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.4,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            import json

            try:
                decoded = json.loads(response_text)

                # Some models wrap the list, e.g. {"flashcards": [...]} or {"cards": [...]}
                if isinstance(decoded, dict):
                    if isinstance(decoded.get("flashcards"), list):
                        flashcards_data = decoded["flashcards"]
                    elif isinstance(decoded.get("cards"), list):
                        flashcards_data = decoded["cards"]
                    else:
                        # Unexpected dict shape; fallback
                        return self._parse_flashcards_fallback(response_text, count)
                elif isinstance(decoded, list):
                    flashcards_data = decoded
                else:
                    # Unsupported top-level type; fallback
                    return self._parse_flashcards_fallback(response_text, count)

                # Normalize items; ignore malformed entries gracefully
                normalized: list[GeneratedFlashcard] = []
                for item in flashcards_data:
                    if isinstance(item, dict):
                        q = item.get("question")
                        a = item.get("answer")
                        if isinstance(q, str) and isinstance(a, str):
                            normalized.append(GeneratedFlashcard(question=q, answer=a))
                    elif isinstance(item, list) and len(item) >= 2:
                        q, a = item[0], item[1]
                        if isinstance(q, str) and isinstance(a, str):
                            normalized.append(GeneratedFlashcard(question=q, answer=a))

                if not normalized:
                    return self._parse_flashcards_fallback(response_text, count)

                return normalized[:count]
            except json.JSONDecodeError:
                # Fallback: extract Q&A pairs manually
                return self._parse_flashcards_fallback(response_text, count)

        except Exception as e:
            logger.error(f"Error in generate_flashcards: {e!s}")
            raise Exception(f"Failed to generate flashcards: {e!s}") from e

    def _parse_flashcards_fallback(
        self, text: str, count: int
    ) -> list[GeneratedFlashcard]:
        """Fallback parser for flashcards when JSON parsing fails"""
        flashcards = []
        lines = text.split("\n")

        current_question = None
        current_answer = None

        for line in lines:
            line = line.strip()
            if line.startswith("Q:") or line.startswith("Question:"):
                if current_question and current_answer:
                    flashcards.append(
                        GeneratedFlashcard(
                            question=current_question, answer=current_answer
                        )
                    )
                current_question = line.split(":", 1)[1].strip()
                current_answer = None
            elif line.startswith("A:") or line.startswith("Answer:"):
                current_answer = line.split(":", 1)[1].strip()

        # Add the last flashcard
        if current_question and current_answer:
            flashcards.append(
                GeneratedFlashcard(question=current_question, answer=current_answer)
            )

        # If still no flashcards, create simple ones
        if not flashcards:
            flashcards = [
                GeneratedFlashcard(
                    question="What are the main points of this content?",
                    answer="Please review the original content for key concepts.",
                )
            ]

        return flashcards[:count]

    def calculate_similarity(self, texts: list[str]) -> np.ndarray:
        """Calculate similarity matrix between texts using TF-IDF"""
        if len(texts) < 2:
            return np.array([[1.0]])

        try:
            # Create TF-IDF vectors
            # More permissive vectorizer to make similarity matching easier
            vectorizer = TfidfVectorizer(
                max_features=3000,
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
                norm="l2",
            )

            tfidf_matrix = vectorizer.fit_transform(texts)

            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            # Calibrate similarities to be less strict: boost medium sims upward
            # boosted = min(1, sqrt(sim) * 1.1)
            boosted = np.minimum(1.0, np.sqrt(np.maximum(similarity_matrix, 0.0)) * 1.1)

            return boosted

        except Exception as e:
            logger.error(f"Error calculating similarity: {e!s}")
            # Return identity matrix as fallback
            n = len(texts)
            return np.eye(n)

    def find_note_connections(
        self, notes: list[dict[str, Any]], threshold: float = 0.6
    ) -> list[dict[str, Any]]:
        """Find connections between notes based on content similarity"""
        if len(notes) < 2:
            return []

        # Extract text content for similarity calculation
        texts = [f"{note['title']} {note['content']}" for note in notes]

        # Calculate similarity matrix
        similarity_matrix = self.calculate_similarity(texts)

        connections = []
        n = len(notes)

        for i in range(n):
            for j in range(i + 1, n):
                similarity = similarity_matrix[i][j]

                if similarity > threshold:
                    connections.append(
                        {
                            "source_id": notes[i]["id"],
                            "target_id": notes[j]["id"],
                            "similarity": float(similarity),
                            "connection_type": "similarity",
                        }
                    )

        # Sort by similarity (highest first)
        connections.sort(key=lambda x: x["similarity"], reverse=True)

        return connections


# Global AI service instance
ai_service = AIService()


# Convenience functions
async def summarize_content(content: str) -> str:
    """Summarize text content"""
    return await ai_service.summarize_text(content)


async def generate_flashcards_from_content(
    content: str, count: int = 5
) -> list[GeneratedFlashcard]:
    """Generate flashcards from content"""
    return await ai_service.generate_flashcards(content, count)


def calculate_note_similarities(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate similarities between notes"""
    return ai_service.find_note_connections(notes)
