<template>
  <span class="citation-wrapper" @mouseenter="showTooltip" @mouseleave="hideTooltip">
    <!-- 引用标记 [1] -->
    <span 
      class="citation-marker"
      :class="{ 'citation-marker-active': isVisible }"
    >
      [{{ citationId }}]
    </span>
    
    <!-- 悬浮卡片 -->
    <Transition name="tooltip-fade">
      <div 
        v-if="isVisible" 
        class="citation-tooltip"
        :style="tooltipStyle"
      >
        <!-- 箭头 -->
        <div class="tooltip-arrow"></div>
        
        <!-- 卡片内容 -->
        <div class="tooltip-content">
          <!-- 标题行 -->
          <div class="tooltip-header">
            <span class="citation-badge">[{{ citationId }}]</span>
            <span class="doc-name" :title="source.doc_name || source.docName">
              {{ truncate(source.doc_name || source.docName || '未知文档', 30) }}
            </span>
          </div>
          
          <!-- 学术信息 (如果有) -->
          <div v-if="source.paper_title || source.paperTitle" class="paper-info">
            <div class="paper-title">{{ truncate(source.paper_title || source.paperTitle, 60) }}</div>
            <div v-if="source.authors" class="paper-authors">
              {{ formatAuthors(source.authors) }}
              <span v-if="source.publication_year || source.publicationYear" class="paper-year">
                ({{ source.publication_year || source.publicationYear }})
              </span>
            </div>
          </div>
          
          <!-- 位置信息 -->
          <div class="location-info">
            <span v-if="source.page_number || source.pageNumber" class="location-item">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              第 {{ source.page_number || source.pageNumber }} 页
            </span>
            <span v-if="source.section" class="location-item">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M4 6h16M4 12h16M4 18h7" />
              </svg>
              {{ truncate(source.section, 20) }}
            </span>
          </div>
          
          <!-- 引用原文 -->
          <div v-if="source.cited_text || source.citedText" class="cited-text">
            <div class="cited-text-label">引用原文:</div>
            <div class="cited-text-content">
              "{{ truncate(source.cited_text || source.citedText, 150) }}"
            </div>
          </div>
          
          <!-- 来源链接 -->
          <div v-if="source.source_url || source.sourceUrl" class="source-link">
            <a :href="source.source_url || source.sourceUrl" target="_blank" rel="noopener noreferrer">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              查看原文
            </a>
          </div>
        </div>
      </div>
    </Transition>
  </span>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  citationId: {
    type: Number,
    required: true
  },
  source: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

const isVisible = ref(false)
let hideTimeout = null

const tooltipStyle = computed(() => ({
  // 可以根据需要动态调整位置
}))

const showTooltip = () => {
  if (hideTimeout) {
    clearTimeout(hideTimeout)
    hideTimeout = null
  }
  isVisible.value = true
}

const hideTooltip = () => {
  // 添加延迟，让用户可以移动到tooltip上
  hideTimeout = setTimeout(() => {
    isVisible.value = false
  }, 200)
}

const truncate = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const formatAuthors = (authors) => {
  if (!authors) return ''
  if (typeof authors === 'string') return authors
  if (!Array.isArray(authors)) return ''
  
  if (authors.length > 2) {
    return `${authors[0]} 等`
  }
  return authors.join(', ')
}
</script>

<style scoped>
.citation-wrapper {
  position: relative;
  display: inline;
}

.citation-marker {
  color: #2563eb;
  font-weight: 500;
  cursor: pointer;
  padding: 0 2px;
  border-radius: 3px;
  transition: all 0.2s ease;
  font-size: 0.85em;
  vertical-align: super;
  line-height: 0;
}

.citation-marker:hover,
.citation-marker-active {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.citation-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 320px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 
              0 8px 10px -6px rgba(0, 0, 0, 0.1);
  z-index: 100;
  padding: 0;
  overflow: hidden;
}

.tooltip-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 12px;
  height: 12px;
  background: white;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.tooltip-content {
  padding: 12px 14px;
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.citation-badge {
  background: #2563eb;
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.doc-name {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.paper-info {
  background: #f9fafb;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
}

.paper-title {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
  line-height: 1.4;
}

.paper-authors {
  font-size: 11px;
  color: #6b7280;
}

.paper-year {
  color: #9ca3af;
}

.location-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.location-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #6b7280;
}

.icon {
  width: 14px;
  height: 14px;
  stroke-width: 2;
}

.cited-text {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding: 8px 10px;
  border-radius: 0 6px 6px 0;
  margin-bottom: 8px;
}

.cited-text-label {
  font-size: 10px;
  color: #92400e;
  font-weight: 500;
  margin-bottom: 4px;
  text-transform: uppercase;
}

.cited-text-content {
  font-size: 12px;
  color: #78350f;
  line-height: 1.5;
  font-style: italic;
}

.source-link {
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.source-link a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #2563eb;
  text-decoration: none;
  transition: color 0.2s;
}

.source-link a:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

/* 动画 */
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}
</style>
