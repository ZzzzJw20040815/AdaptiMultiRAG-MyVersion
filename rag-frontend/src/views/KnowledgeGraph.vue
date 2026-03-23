<template>
  <div class="knowledge-graph-container">
    <!-- 页面头部 -->
    <div class="header">
      <div class="header-left">
        <el-button @click="goBack" type="primary" plain>
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h1 class="title">知识图谱</h1>
      </div>
      <div class="controls">
        <el-select
          v-model="selectedLabel"
          placeholder="选择标签"
          @change="loadGraphData"
          style="width: 200px; margin-right: 16px;"
        >
          <el-option label="全部" value="*" />
          <el-option
            v-for="label in availableLabels"
            :key="label"
            :label="label"
            :value="label"
          />
        </el-select>
        <el-button @click="refreshGraph" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 过滤控制面板 -->
    <div class="filter-panel">
      <div class="filter-section">
        <span class="filter-label">智能过滤:</span>
        <el-switch
          v-model="enableFilter"
          active-text="开启"
          inactive-text="关闭"
          @change="loadGraphData"
        />
      </div>
      
      <div class="filter-section" v-show="enableFilter">
        <span class="filter-label">最小连接数:</span>
        <el-slider
          v-model="minEdgeCount"
          :min="0"
          :max="10"
          :step="1"
          :marks="{ 0: '0', 5: '5', 10: '10' }"
          style="width: 150px;"
          @change="loadGraphData"
        />
        <span class="filter-value">{{ minEdgeCount }}</span>
      </div>
      
      <div class="filter-section">
        <span class="filter-label">节点类型:</span>
        <el-select
          v-model="selectedTypes"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择显示的类型"
          style="width: 200px;"
          @change="applyFrontendFilter"
        >
          <el-option
            v-for="nodeType in availableNodeTypes"
            :key="nodeType"
            :label="nodeType"
            :value="nodeType"
          />
        </el-select>
      </div>
      
      <div class="filter-section">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索节点..."
          style="width: 180px;"
          clearable
          @input="applySearchHighlight"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 图谱容器 -->
    <div class="graph-container">
      <div
        ref="chartContainer"
        class="chart"
        v-loading="loading"
        element-loading-text="正在加载知识图谱..."
      ></div>
      
      <!-- 缩放控制按钮 -->
      <div class="zoom-controls">
        <el-button-group>
          <el-button @click="zoomIn" :icon="ZoomIn" title="放大" />
          <el-button @click="zoomOut" :icon="ZoomOut" title="缩小" />
          <el-button @click="resetZoom" :icon="Refresh" title="重置视图" />
        </el-button-group>
        <div class="zoom-level">{{ Math.round(currentZoom * 100) }}%</div>
        <div class="pan-hint">右键拖动平移</div>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="stats" v-if="graphStats">
      <div class="stat-item">
        <span class="label">节点数量:</span>
        <span class="value">{{ graphStats.displayedNodeCount }} / {{ graphStats.totalNodeCount }}</span>
      </div>
      <div class="stat-item">
        <span class="label">关系数量:</span>
        <span class="value">{{ graphStats.displayedEdgeCount }} / {{ graphStats.totalEdgeCount }}</span>
      </div>
      <div class="stat-item">
        <span class="label">标签类型:</span>
        <span class="value">{{ graphStats.labelCount }}</span>
      </div>
      <div class="stat-item" v-if="enableFilter">
        <span class="label">已过滤:</span>
        <span class="value filtered">{{ graphStats.filteredCount }} 节点</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, ArrowLeft, Search, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { knowledgeAPI } from '@/api/knowledge.js'

// 响应式数据
const route = useRoute()
const router = useRouter()
const chartContainer = ref(null)
const loading = ref(false)
const selectedLabel = ref('*')
const availableLabels = ref([])
const graphStats = ref(null)

// 过滤相关状态
const enableFilter = ref(true)
const minEdgeCount = ref(0)
const selectedTypes = ref([])
const availableNodeTypes = ref([])
const searchKeyword = ref('')

// 缩放相关状态
const currentZoom = ref(1)
const minZoom = 0.1
const maxZoom = 5
const zoomStep = 0.05  // 每次点击按钮放大/缩小 5%

// 平移相关状态
let isPanning = false
let panStartX = 0
let panStartY = 0

// 原始数据存储
let rawGraphData = null

// ECharts实例
let chartInstance = null

// 获取知识库ID
const collectionId = route.params.collection_id || route.query.collection_id

// 加载图谱数据
const loadGraphData = async () => {
  if (!collectionId) {
    ElMessage.error('缺少知识库ID参数')
    return
  }

  loading.value = true
  try {
    const response = await knowledgeAPI.getKnowledgeGraph(
      collectionId, 
      selectedLabel.value,
      {
        enableFilter: enableFilter.value,
        minEdgeCount: minEdgeCount.value
      }
    )
    const graphData = response.data || response
    
    // 保存原始数据
    rawGraphData = graphData
    
    // 处理图谱数据
    processGraphData(graphData)
    
    // 初始化节点类型选项
    initNodeTypes(graphData)
    
    // 更新统计信息
    updateStats(graphData, graphData)
    
    // 渲染图谱（应用前端过滤）
    applyFrontendFilter()
    
  } catch (error) {
    console.error('加载知识图谱失败:', error)
    ElMessage.error('加载知识图谱失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 处理图谱数据
const processGraphData = (data) => {
  // 提取所有可用的标签
  const labels = new Set()
  if (data.nodes) {
    data.nodes.forEach(node => {
      if (node.labels && Array.isArray(node.labels)) {
        node.labels.forEach(label => labels.add(label))
      }
    })
  }
  availableLabels.value = Array.from(labels).sort()
}

// 初始化节点类型选项（使用后端返回的语义类型）
const initNodeTypes = (data) => {
  const types = new Set()
  if (data.nodes) {
    data.nodes.forEach(node => {
      // 优先使用后端分类的语义类型，回退到原始标签
      const category = node.properties?.semantic_type || node.labels?.[0] || '其他'
      types.add(category)
    })
  }
  availableNodeTypes.value = Array.from(types).sort()
  // 默认只显示5个重要类型
  if (selectedTypes.value.length === 0) {
    const importantTypes = ['任务', '工具/系统', '技术/方法', '模型', '研究工作']
    selectedTypes.value = importantTypes.filter(type => availableNodeTypes.value.includes(type))
    // 如果没有匹配的重要类型，则显示所有类型
    if (selectedTypes.value.length === 0) {
      selectedTypes.value = [...availableNodeTypes.value]
    }
  }
}

// 应用前端过滤
const applyFrontendFilter = () => {
  if (!rawGraphData) return
  
  let filteredNodes = rawGraphData.nodes || []
  let filteredEdges = rawGraphData.edges || []
  
  // 按类型过滤（使用语义类型）
  if (selectedTypes.value.length > 0 && selectedTypes.value.length < availableNodeTypes.value.length) {
    const selectedSet = new Set(selectedTypes.value)
    filteredNodes = filteredNodes.filter(node => {
      const category = node.properties?.semantic_type || node.labels?.[0] || '其他'
      return selectedSet.has(category)
    })
    
    // 同步删除悬空边
    const nodeIds = new Set(filteredNodes.map(n => n.id))
    filteredEdges = filteredEdges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    )
  }
  
  const filteredData = {
    nodes: filteredNodes,
    edges: filteredEdges,
    is_truncated: rawGraphData.is_truncated
  }
  
  // 更新统计
  updateStats(rawGraphData, filteredData)
  
  // 渲染图谱
  renderGraph(filteredData)
}

// 应用搜索高亮
const applySearchHighlight = () => {
  if (!chartInstance) return
  
  const keyword = searchKeyword.value.toLowerCase().trim()
  
  if (!keyword) {
    // 无搜索词时重置高亮
    applyFrontendFilter()
    return
  }
  
  // 获取当前选项
  const option = chartInstance.getOption()
  if (!option || !option.series || !option.series[0]) return
  
  const nodes = option.series[0].data || []
  
  // 更新节点样式以高亮匹配项
  const updatedNodes = nodes.map(node => {
    const name = (node.name || '').toLowerCase()
    // 只匹配节点名称，不匹配描述
    const isMatch = name.includes(keyword)
    
    return {
      ...node,
      itemStyle: {
        ...node.itemStyle,
        opacity: isMatch ? 1 : 0.3,
        borderWidth: isMatch ? 3 : 0,
        borderColor: isMatch ? '#ff6b6b' : undefined
      },
      label: {
        ...node.label,
        fontWeight: isMatch ? 'bold' : 'normal',
        color: isMatch ? '#c92a2a' : undefined
      }
    }
  })
  
  chartInstance.setOption({
    series: [{
      data: updatedNodes
    }]
  })
}

// 更新统计信息
const updateStats = (originalData, displayedData) => {
  // 优先使用后端返回的过滤统计信息
  const filterStats = originalData.filter_stats
  
  let totalNodeCount, totalEdgeCount, displayedNodeCount, displayedEdgeCount
  
  if (filterStats) {
    // 使用后端的过滤统计 - 原始数量来自后端过滤前
    totalNodeCount = filterStats.original_node_count
    totalEdgeCount = filterStats.original_edge_count
    // 当前显示的数量 = 前端显示的数量（可能经过前端二次过滤）
    displayedNodeCount = displayedData.nodes ? displayedData.nodes.length : 0
    displayedEdgeCount = displayedData.edges ? displayedData.edges.length : 0
  } else {
    // 回退：没有后端统计时使用本地计算
    totalNodeCount = originalData.nodes ? originalData.nodes.length : 0
    totalEdgeCount = originalData.edges ? originalData.edges.length : 0
    displayedNodeCount = displayedData.nodes ? displayedData.nodes.length : 0
    displayedEdgeCount = displayedData.edges ? displayedData.edges.length : 0
  }
  
  graphStats.value = {
    totalNodeCount,
    totalEdgeCount,
    displayedNodeCount,
    displayedEdgeCount,
    labelCount: availableLabels.value.length,
    filteredCount: totalNodeCount - displayedNodeCount
  }
}

// 渲染图谱
const renderGraph = (data) => {
  if (!chartInstance || !data.nodes) return

  // 重置缩放状态（因为 setOption(option, true) 会重置图表，包括缩放）
  currentZoom.value = 1

  // 处理节点数据（使用语义类型作为分类）
  const nodes = data.nodes.map(node => {
    const semanticType = node.properties?.semantic_type || node.labels?.[0] || '其他'
    return {
      id: node.id,
      name: node.properties?.entity_id || node.id,
      value: node.properties?.description || '',
      category: semanticType,
      symbolSize: Math.min(Math.max(20, (node.properties?.description?.length || 100) / 10), 80),
      itemStyle: {
        color: getNodeColor(semanticType)
      },
      label: {
        show: true,
        fontSize: 12
      }
    }
  })

  // 处理边数据
  const links = data.edges ? data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    name: edge.type || 'RELATED',
    lineStyle: {
      color: '#999',
      width: 2
    }
  })) : []

  // 创建分类数据
  const categories = [...new Set(nodes.map(node => node.category))].map(cat => ({
    name: cat,
    itemStyle: {
      color: getNodeColor(cat)
    }
  }))

  // ECharts配置
  const option = {
    title: {
      text: `知识图谱 (${selectedLabel.value === '*' ? '全部' : selectedLabel.value})`,
      left: 'center',
      textStyle: {
        fontSize: 18,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      enterable: true,
      formatter: function(params) {
        if (params.dataType === 'node') {
          const description = params.data.value ? params.data.value.replace(/\n/g, '<br/>') : '暂无描述';
          const showType = params.data.category && params.data.name && params.data.category.toLowerCase() !== params.data.name.toLowerCase();
          const typeHtml = showType ? `<span style="color: #666;">类型: ${params.data.category}</span><br/>` : '';
          
          return `
            <div style="max-width: 400px; white-space: normal; word-break: break-word;">
              <strong>${params.data.name}</strong><br/>
              ${typeHtml}
              <div style="margin-top: 8px; line-height: 1.5;">
                ${description}
              </div>
            </div>
          `
        } else if (params.dataType === 'edge') {
          return `关系: ${params.data.name}`
        }
      }
    },
    legend: {
      show: false
    },
    series: [{
      name: '知识图谱',
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      categories: categories,
      roam: 'move',  // 只启用平移，禁用默认滚轮缩放
      focusNodeAdjacency: true,
      draggable: true,
      scaleLimit: {
        min: minZoom,
        max: maxZoom
      },
      force: {
        repulsion: 1000,
        gravity: 0.1,
        edgeLength: [50, 200],
        layoutAnimation: true
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{b}'
      },
      lineStyle: {
        color: 'source',
        curveness: 0.3
      },
      emphasis: {
        disabled: true
      }
    }]
  }

  chartInstance.setOption(option, true)
}

// 获取节点颜色
const getNodeColor = (category) => {
  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f'
  ]
  const hash = category ? category.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0)
    return a & a
  }, 0) : 0
  return colors[Math.abs(hash) % colors.length]
}

// 刷新图谱
const refreshGraph = () => {
  loadGraphData()
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 缩放控制函数
const zoomIn = () => {
  if (!chartInstance) return
  const newZoom = Math.min(currentZoom.value + zoomStep, maxZoom)
  applyZoom(newZoom)
}

const zoomOut = () => {
  if (!chartInstance) return
  const newZoom = Math.max(currentZoom.value - zoomStep, minZoom)
  applyZoom(newZoom)
}

const resetZoom = () => {
  if (!chartInstance) return
  applyZoom(1)
  // 重置位置到中心
  chartInstance.dispatchAction({
    type: 'graphRoam',
    seriesIndex: 0,
    zoom: 1,
    originX: chartContainer.value.clientWidth / 2,
    originY: chartContainer.value.clientHeight / 2
  })
}

const applyZoom = (zoom) => {
  if (!chartInstance) return
  const zoomRatio = zoom / currentZoom.value
  currentZoom.value = zoom
  
  chartInstance.dispatchAction({
    type: 'graphRoam',
    seriesIndex: 0,
    zoom: zoomRatio,
    originX: chartContainer.value.clientWidth / 2,
    originY: chartContainer.value.clientHeight / 2
  })
}

// 自定义滚轮缩放处理（大幅降低灵敏度）
const handleWheel = (event) => {
  if (!chartInstance || !chartContainer.value) return
  
  // 检查是否在图表区域内
  const rect = chartContainer.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right ||
      event.clientY < rect.top || event.clientY > rect.bottom) {
    return
  }
  
  event.preventDefault()
  
  // 大幅降低滚轮灵敏度：
  // 1. 标准化 deltaY（不同浏览器/设备的 deltaY 值差异很大）
  // 2. 使用更小的缩放步长
  const normalizedDelta = Math.sign(event.deltaY)  // 只取方向（-1 或 1）
  const scrollSensitivity = 0.05  // 每次滚轮放大/缩小 5%
  const delta = -normalizedDelta * scrollSensitivity
  const newZoom = Math.max(minZoom, Math.min(maxZoom, currentZoom.value + delta))
  
  if (newZoom !== currentZoom.value) {
    const zoomRatio = newZoom / currentZoom.value
    currentZoom.value = newZoom
    
    // 以鼠标位置为中心进行缩放
    chartInstance.dispatchAction({
      type: 'graphRoam',
      seriesIndex: 0,
      zoom: zoomRatio,
      originX: event.clientX - rect.left,
      originY: event.clientY - rect.top
    })
  }
}

// 右键拖动平移处理
const handleMouseDown = (event) => {
  if (!chartInstance || !chartContainer.value) return
  
  // 右键（button === 2）或中键（button === 1）触发平移
  if (event.button === 2 || event.button === 1) {
    event.preventDefault()
    isPanning = true
    panStartX = event.clientX
    panStartY = event.clientY
    chartContainer.value.style.cursor = 'grabbing'
  }
}

const handleMouseMove = (event) => {
  if (!isPanning || !chartInstance || !chartContainer.value) return
  
  const deltaX = event.clientX - panStartX
  const deltaY = event.clientY - panStartY
  
  // 更新起始点
  panStartX = event.clientX
  panStartY = event.clientY
  
  // 应用平移
  chartInstance.dispatchAction({
    type: 'graphRoam',
    seriesIndex: 0,
    dx: deltaX,
    dy: deltaY
  })
}

const handleMouseUp = (event) => {
  if (isPanning) {
    isPanning = false
    if (chartContainer.value) {
      chartContainer.value.style.cursor = 'grab'
    }
  }
}

// 禁止右键菜单
const handleContextMenu = (event) => {
  event.preventDefault()
}

// 初始化图表
const initChart = async () => {
  await nextTick()
  if (chartContainer.value) {
    chartInstance = echarts.init(chartContainer.value)
    
    // 添加自定义滚轮缩放处理
    chartContainer.value.addEventListener('wheel', handleWheel, { passive: false })
    
    // 添加右键拖动平移处理
    chartContainer.value.addEventListener('mousedown', handleMouseDown)
    chartContainer.value.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      chartInstance?.resize()
    })
  }
}

// 组件挂载
onMounted(async () => {
  await initChart()
  await loadGraphData()
})

// 组件卸载
onUnmounted(() => {
  // 移除事件监听
  if (chartContainer.value) {
    chartContainer.value.removeEventListener('wheel', handleWheel)
    chartContainer.value.removeEventListener('mousedown', handleMouseDown)
    chartContainer.value.removeEventListener('contextmenu', handleContextMenu)
  }
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
  })
})
</script>

<style scoped>
.knowledge-graph-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.controls {
  display: flex;
  align-items: center;
}

/* 过滤控制面板样式 */
.filter-panel {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 20px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  flex-wrap: wrap;
}

.filter-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

.filter-value {
  color: #333;
  font-weight: 500;
  min-width: 20px;
  text-align: center;
}

.graph-container {
  flex: 1;
  padding: 20px;
  overflow: hidden;
  position: relative;
}

.chart {
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: grab;
}

.chart:active {
  cursor: grabbing;
}

/* 缩放控制按钮样式 */
.zoom-controls {
  position: absolute;
  bottom: 40px;
  right: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  z-index: 100;
}

.zoom-controls .el-button-group {
  display: flex;
  flex-direction: column;
}

.zoom-controls .el-button-group .el-button {
  margin-left: 0;
  border-radius: 0;
}

.zoom-controls .el-button-group .el-button:first-child {
  border-radius: 4px 4px 0 0;
}

.zoom-controls .el-button-group .el-button:last-child {
  border-radius: 0 0 4px 4px;
}

.zoom-level {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.pan-hint {
  font-size: 11px;
  color: #999;
  border-top: 1px solid #eee;
  padding-top: 8px;
  margin-top: 4px;
}

.stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-item .label {
  color: #666;
  font-size: 14px;
}

.stat-item .value {
  color: #333;
  font-weight: bold;
  font-size: 16px;
}

.stat-item .value.filtered {
  color: #e6a23c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .controls {
    justify-content: center;
  }
  
  .filter-panel {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .stats {
    flex-direction: column;
    gap: 12px;
    align-items: center;
  }
}
</style>