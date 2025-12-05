"""
API router for AI chat and RAG retrieval.

Handles natural language queries, performs vector search in ChromaDB,
and generates responses using the LLM in a streaming fashion.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime 
import locale

from .. import auth, models, schemas, ai
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
)

@router.post("")
async def chat_with_gallery(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs a RAG search and streams the answer.

    Flow:
    1. [Async] Convert user query to vector embedding.
    2. [Sync] Search ChromaDB for most similar images filtered by user_id).
    3. Construct a prompt with image metadata and Markdown instructions.
    4. [Async/Stream] Stream LLM response to client.

    Args:
        request: The user's query string.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StreamingResponse: A stream of text chunks.
    """
    # 1. Generate Embedding for the query
    try:
        query_vector = await ai.generate_embedding(request.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service error: {str(e)}"
        )

    # 2. Vector Search in ChromaDB
    # We retrieve top 5 results to give LLM enough context
    collection = ai.get_chroma_collection()
    
    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=5,
            where={"user_id": current_user.id}, # User can only access his own images
            include=["metadatas", "distances"]
        )
    except Exception as e:
        # If collection is empty or other DB error
        print(f"ChromaDB Query Error: {e}")
        def error_generator():
            yield "抱歉，搜索服务暂时不可用，或者您的相册中还没有已索引的图片。"
        return StreamingResponse(error_generator(), media_type="text/plain")

    # Parse results
    context_parts = []
    
    # Check if we got any results
    if results["ids"] and results["ids"][0]:
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i in range(len(ids)):
            image_id = int(ids[i])
            meta = metadatas[i]
            dist = distances[i]
            
            thumbnail_url = meta.get("thumbnail_url", "")
            description_text = meta.get("text", "")
            relevance_hint = f"距离 {dist:.3f} (越小越好)"
            
            # Provide the LLM with the exact Markdown syntax to use
            context_parts.append(
                f"- [Image Info] ID: {image_id}\n"
                f"  匹配度参考: {relevance_hint}\n"
                f"  描述: {description_text}\n"
                f"  Markdown引用代码: ![{image_id}]({thumbnail_url})\n"
            )

    context_str = "\n".join(context_parts)

    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_str = weekdays[now.weekday()]
    current_time_str = now.strftime(f"%Y年%m月%d日 {weekday_str} %H:%M")
    
    # 3. Construct RAG Prompt with Markdown Instructions
    prompt = f"""
    [环境信息]
    当前时间：{current_time_str}
    当前用户：{current_user.username}

    用户正在寻找："{request.query}"

    以下是我在用户相册中为您检索到的几张最相关的图片信息（按相关性排序）：
    {context_str}

    请遵循以下规则回答：
    0. 避免使用“用户”来称呼用户，而应改用[当前用户]的名称。
    1. 用自然流畅的简体中文回答用户，语言风格轻松，多用生活惯用语。
    2. 告诉用户你找到了什么。
    3. 如果你提到的图片在上述列表中，请务必直接使用提供的 [Markdown引用代码] 将图片展示出来。
       例如： "我找到了一张照片：![99](/api/v1/images/99/thumbnail)"。
    4. 不要只列出ID，要让回复看起来图文并茂。
    5. 请参考每张图片的[匹配度参考]，注意这个信息不应告知用户。如果所有图片的距离都比较大（例如大于 1.0），这说明数据库中可能没有真正相关的图片。在这种情况下，请礼貌地告知用户可能没有找到完全匹配的结果。你不需要将这张看似不相关的图片提供给用户，只需要简要告知用户这张不相关的图片的关键词，并建议用户尝试用这个关键词来搜索。
    6. 当请求中包含时间时，你需要参考[当前时间]，并给出计算依据。对于非图片检索的用户要求，请礼貌拒绝用户，告知用户自己无法完成这个请求。除此之外，请不要回复更多内容，包括提供图片信息。
    """

    # 4. Stream the Response
    return StreamingResponse(
        ai.query_llm_stream(prompt), 
        media_type="text/event-stream"
    )