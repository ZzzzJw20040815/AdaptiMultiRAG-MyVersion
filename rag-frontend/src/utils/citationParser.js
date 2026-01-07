/**
 * Citation Parsing Utilities (PR-8)
 * 
 * 解析回答文本中的 [1][2] 引用标记，并提供渲染辅助函数
 */

/**
 * 从文本中提取所有引用标记
 * @param {string} text - 原始文本
 * @returns {Array} 引用标记数组 [{id: 1, position: 0}, ...]
 */
export function extractCitations(text) {
    if (!text) return []

    const regex = /\[(\d+)\]/g
    const citations = []
    let match

    while ((match = regex.exec(text)) !== null) {
        citations.push({
            id: parseInt(match[1], 10),
            position: match.index,
            fullMatch: match[0]
        })
    }

    return citations
}

/**
 * 将引用标记转换为可交互的 HTML
 * @param {string} text - 原始文本
 * @param {Array} sources - 引用来源数组
 * @returns {string} 转换后的 HTML
 */
export function formatCitationsAsHtml(text, sources = []) {
    if (!text) return ''

    // 将 [1], [2] 等标记替换为带 data 属性的 span
    return text.replace(/\[(\d+)\]/g, (match, num) => {
        const citationId = parseInt(num, 10)
        const source = sources.find(s => s.citation_id === citationId || s.citationId === citationId)

        // 构建 tooltip 数据
        const tooltipData = source ? encodeURIComponent(JSON.stringify(source)) : ''

        return `<span class="citation-inline" data-citation-id="${citationId}" data-source="${tooltipData}">${match}</span>`
    })
}

/**
 * 使用 Vue 组件方式渲染引用
 * 返回分段后的文本和引用信息
 * @param {string} text - 原始文本
 * @param {Array} sources - 引用来源数组
 * @returns {Array} 分段数组 [{type: 'text', content: '...'}, {type: 'citation', id: 1, source: {...}}]
 */
export function parseCitationSegments(text, sources = []) {
    if (!text) return []

    const segments = []
    const regex = /\[(\d+)\]/g
    let lastIndex = 0
    let match

    while ((match = regex.exec(text)) !== null) {
        // 添加前面的纯文本
        if (match.index > lastIndex) {
            segments.push({
                type: 'text',
                content: text.substring(lastIndex, match.index)
            })
        }

        // 添加引用
        const citationId = parseInt(match[1], 10)
        const source = sources.find(s =>
            (s.citation_id === citationId) ||
            (s.citationId === citationId) ||
            (s.doc_index === citationId - 1)
        ) || {}

        segments.push({
            type: 'citation',
            id: citationId,
            source: source
        })

        lastIndex = regex.lastIndex
    }

    // 添加剩余文本
    if (lastIndex < text.length) {
        segments.push({
            type: 'text',
            content: text.substring(lastIndex)
        })
    }

    return segments
}

/**
 * 判断文本是否包含引用标记
 * @param {string} text - 原始文本
 * @returns {boolean}
 */
export function hasCitations(text) {
    if (!text) return false
    return /\[\d+\]/.test(text)
}

/**
 * 获取引用来源的显示名称
 * @param {Object} source - 引用来源对象
 * @returns {string} 显示名称
 */
export function getCitationDisplayName(source) {
    if (!source) return '未知来源'

    const parts = []

    // 论文标题或文档名
    if (source.paper_title || source.paperTitle) {
        parts.push(`"${(source.paper_title || source.paperTitle).substring(0, 40)}..."`)
    } else if (source.doc_name || source.docName) {
        parts.push(source.doc_name || source.docName)
    }

    // 作者
    if (source.authors && Array.isArray(source.authors) && source.authors.length > 0) {
        parts.push(source.authors.length > 2 ? `${source.authors[0]} 等` : source.authors.join(', '))
    }

    // 年份
    if (source.publication_year || source.publicationYear) {
        parts.push(`(${source.publication_year || source.publicationYear})`)
    }

    // 页码
    if (source.page_number || source.pageNumber) {
        parts.push(`p.${source.page_number || source.pageNumber}`)
    }

    return parts.length > 0 ? parts.join(' ') : '来源未知'
}

export default {
    extractCitations,
    formatCitationsAsHtml,
    parseCitationSegments,
    hasCitations,
    getCitationDisplayName
}
