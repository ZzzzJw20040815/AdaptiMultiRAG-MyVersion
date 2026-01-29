from fastapi import APIRouter, Depends, Query
from backend.config.log import get_logger
from backend.config.dependencies import get_current_user
from backend.service.visual_graph import VisualGraphService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/visual",
    tags=["VISUAL_GRAPH"]
)

@router.get("/graph/{collection_id}")
async def get_visual_graph(
    collection_id: str,
    label: str = Query(..., description="Label to get knowledge graph for"),
    enable_filter: bool = Query(True, description="是否启用节点过滤"),
    min_edge_count: int = Query(0, ge=0, le=20, description="最小连接数过滤（0表示不过滤）"),
    current_user: int = Depends(get_current_user),
):
    """
    获取知识库的可视化图
    
    Args:
        collection_id: 知识库集合ID
        label: 节点标签筛选
        enable_filter: 是否启用节点过滤（关键词、正则、标签等过滤规则）
        min_edge_count: 最小连接数，低于此值的节点将被过滤
    """
    logger.info(f"用户 {current_user} 请求获取知识库 {collection_id} 的可视化图，label={label}, enable_filter={enable_filter}, min_edge_count={min_edge_count}")
    visualgraph = VisualGraphService(collection_id)
    return await visualgraph.get_knowledge_graph(
        node_label=label,
        enable_filter=enable_filter,
        min_edge_count=min_edge_count
    )

