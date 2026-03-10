from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Topic, TopicRule


@dataclass
class TopicPreset:
    name: str
    description: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    arxiv_categories: list[str]


PRESET_TOPICS: list[TopicPreset] = [
    TopicPreset(
        name="RAG",
        description="Retrieval-augmented generation, vector retrieval, and grounding strategies.",
        include_keywords=["rag", "retrieval augmented", "vector database", "semantic search", "grounded generation"],
        exclude_keywords=[],
        arxiv_categories=["cs.CL", "cs.IR", "cs.AI"],
    ),
    TopicPreset(
        name="Agents",
        description="Tool-using and autonomous LLM agents, planning, and workflows.",
        include_keywords=["agent", "tool use", "function calling", "planner", "multi-agent"],
        exclude_keywords=[],
        arxiv_categories=["cs.AI", "cs.CL"],
    ),
    TopicPreset(
        name="Diffusion",
        description="Diffusion and score-based generative models.",
        include_keywords=["diffusion", "score-based", "ddpm", "latent diffusion"],
        exclude_keywords=[],
        arxiv_categories=["cs.LG", "cs.CV", "stat.ML"],
    ),
    TopicPreset(
        name="Evaluation",
        description="Benchmarks, metrics, eval harnesses, and model validation.",
        include_keywords=["evaluation", "benchmark", "metric", "leaderboard", "judge model"],
        exclude_keywords=[],
        arxiv_categories=["cs.CL", "cs.AI", "cs.LG"],
    ),
    TopicPreset(
        name="Multimodal",
        description="Models over text, image, audio, and video modalities.",
        include_keywords=["multimodal", "vision-language", "vlm", "audio-text", "video-language"],
        exclude_keywords=[],
        arxiv_categories=["cs.CV", "cs.CL", "cs.AI"],
    ),
    TopicPreset(
        name="Inference/Serving",
        description="Inference optimization, quantization, deployment, and serving systems.",
        include_keywords=["inference", "serving", "throughput", "latency", "quantization", "vllm"],
        exclude_keywords=[],
        arxiv_categories=["cs.DC", "cs.LG"],
    ),
    TopicPreset(
        name="Fine-tuning (LoRA/QLoRA)",
        description="Parameter-efficient fine-tuning including LoRA and QLoRA.",
        include_keywords=["fine-tuning", "lora", "qlora", "sft", "adapter"],
        exclude_keywords=[],
        arxiv_categories=["cs.CL", "cs.LG", "stat.ML"],
    ),
    TopicPreset(
        name="Alignment/Safety",
        description="Alignment, harmlessness, robustness, and AI safety methods.",
        include_keywords=["alignment", "safety", "red teaming", "constitutional ai", "harmlessness"],
        exclude_keywords=[],
        arxiv_categories=["cs.AI", "cs.CL"],
    ),
    TopicPreset(
        name="Reinforcement Learning",
        description="RL methods including policy optimization and RLHF-related work.",
        include_keywords=["reinforcement learning", "rlhf", "policy gradient", "actor-critic", "ppo"],
        exclude_keywords=[],
        arxiv_categories=["cs.LG", "cs.AI", "stat.ML"],
    ),
    TopicPreset(
        name="Computer Vision",
        description="Vision models, recognition, segmentation, and visual reasoning.",
        include_keywords=["computer vision", "segmentation", "object detection", "image classification", "vision transformer"],
        exclude_keywords=[],
        arxiv_categories=["cs.CV"],
    ),
]


def seed_topics() -> tuple[int, int]:
    created_topics = 0
    upserted_rules = 0

    with SessionLocal() as db:
        for preset in PRESET_TOPICS:
            topic = db.execute(select(Topic).where(Topic.name == preset.name)).scalar_one_or_none()
            if topic is None:
                topic = Topic(name=preset.name, description=preset.description)
                db.add(topic)
                db.flush()
                created_topics += 1
            else:
                topic.description = preset.description

            rule = db.execute(select(TopicRule).where(TopicRule.topic_id == topic.id)).scalar_one_or_none()
            if rule is None:
                rule = TopicRule(
                    topic_id=topic.id,
                    include_keywords=preset.include_keywords,
                    exclude_keywords=preset.exclude_keywords,
                    arxiv_categories=preset.arxiv_categories,
                )
                db.add(rule)
            else:
                rule.include_keywords = preset.include_keywords
                rule.exclude_keywords = preset.exclude_keywords
                rule.arxiv_categories = preset.arxiv_categories
            upserted_rules += 1

        db.commit()

    return created_topics, upserted_rules


def main() -> None:
    created_topics, upserted_rules = seed_topics()
    print(f"Seed summary: created_topics={created_topics}, upserted_rules={upserted_rules}")


if __name__ == "__main__":
    main()
