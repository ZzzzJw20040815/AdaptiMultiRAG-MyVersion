/**
 * 知识图谱任务 API
 * 提供知识图谱构建任务的启动、暂停、恢复、取消和状态查询
 */

import { httpClient } from './config.js'

/**
 * 获取知识图谱任务状态
 * @param {string} collectionId - 集合ID
 * @returns {Promise} 任务状态
 */
export const getKGTaskStatus = async (collectionId) => {
    try {
        const response = await httpClient.get(`/kg-task/status/${collectionId}`)
        return response.data || response
    } catch (error) {
        console.error('获取知识图谱任务状态失败:', error)
        throw error
    }
}

/**
 * 启动知识图谱构建任务
 * @param {string} collectionId - 集合ID
 * @returns {Promise} 操作结果
 */
export const startKGTask = async (collectionId) => {
    try {
        const response = await httpClient.post(`/kg-task/start/${collectionId}`)
        return response.data || response
    } catch (error) {
        console.error('启动知识图谱构建失败:', error)
        throw error
    }
}

/**
 * 暂停知识图谱构建任务
 * @param {string} collectionId - 集合ID
 * @returns {Promise} 操作结果
 */
export const pauseKGTask = async (collectionId) => {
    try {
        const response = await httpClient.post(`/kg-task/pause/${collectionId}`)
        return response.data || response
    } catch (error) {
        console.error('暂停知识图谱构建失败:', error)
        throw error
    }
}

/**
 * 恢复知识图谱构建任务
 * @param {string} collectionId - 集合ID
 * @returns {Promise} 操作结果
 */
export const resumeKGTask = async (collectionId) => {
    try {
        const response = await httpClient.post(`/kg-task/resume/${collectionId}`)
        return response.data || response
    } catch (error) {
        console.error('恢复知识图谱构建失败:', error)
        throw error
    }
}

/**
 * 取消知识图谱构建任务
 * @param {string} collectionId - 集合ID
 * @returns {Promise} 操作结果
 */
export const cancelKGTask = async (collectionId) => {
    try {
        const response = await httpClient.post(`/kg-task/cancel/${collectionId}`)
        return response.data || response
    } catch (error) {
        console.error('取消知识图谱构建失败:', error)
        throw error
    }
}

export default {
    getKGTaskStatus,
    startKGTask,
    pauseKGTask,
    resumeKGTask,
    cancelKGTask
}
