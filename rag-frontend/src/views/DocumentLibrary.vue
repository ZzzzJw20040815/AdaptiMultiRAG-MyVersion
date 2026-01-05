<template>
  <div class="h-screen flex bg-amber-50/30">
    <!-- 左侧边栏 -->
    <div class="w-80 bg-white border-r border-gray-100 flex flex-col shadow-sm">
      <!-- 头部 -->
      <div class="p-4 border-b border-gray-100">
        <div class="flex items-center justify-between mb-4">
          <h1 class="text-xl font-normal text-gray-900">文档库管理</h1>
          <router-link
            to="/chat"
            class="text-gray-500 hover:text-gray-700 p-2 rounded-lg hover:bg-gray-50"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
          </router-link>
        </div>
        <button
          @click="showCreateDialog = true"
          :disabled="loading"
          class="w-full bg-gray-900 text-white py-2 px-4 rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          新建文档库
        </button>
      </div>

      <!-- 文档库列表 -->
      <div class="flex-1 overflow-y-auto p-4">
        <!-- 加载状态 -->
        <div
          v-if="loading && documentLibraries.length === 0"
          class="flex items-center justify-center py-8"
        >
          <div
            class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"
          ></div>
          <span class="ml-2 text-gray-600 font-light">加载中...</span>
        </div>

        <!-- 错误状态 -->
        <div
          v-else-if="error && documentLibraries.length === 0"
          class="text-center py-8"
        >
          <div class="text-red-500 mb-2 font-light">{{ error }}</div>
          <button
            @click="loadLibraries"
            class="text-gray-900 hover:text-gray-700 text-sm font-normal"
          >
            重新加载
          </button>
        </div>

        <!-- 空状态 -->
        <div
          v-else-if="documentLibraries.length === 0"
          class="text-center py-8 text-gray-500"
        >
          <svg
            class="w-12 h-12 mx-auto mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p class="font-normal">暂无文档库</p>
          <p class="text-sm font-light">点击上方按钮创建第一个文档库</p>
        </div>

        <!-- 文档库列表 -->
        <div v-else class="space-y-2">
          <div
            v-for="library in documentLibraries"
            :key="library.id"
            @click="selectLibrary(library)"
            class="p-3 rounded-lg cursor-pointer transition-colors group border"
            :class="{
              'bg-amber-50 border-amber-200':
                selectedLibrary?.id === library.id,
              'hover:bg-gray-50 border-gray-100':
                selectedLibrary?.id !== library.id,
            }"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <h3 class="text-sm font-normal text-gray-900 truncate">
                  {{ library.title }}
                </h3>
                <p class="text-xs text-gray-500 mt-1 line-clamp-2 font-light">
                  {{ library.description || "暂无描述" }}
                </p>
                <div
                  class="flex items-center mt-2 text-xs text-gray-400 font-light"
                >
                  <span>{{ library.documents?.length || 0 }} 个文档</span>
                  <span class="mx-1">•</span>
                  <span>{{ formatTime(library.updated_at) }}</span>
                </div>
              </div>
              <div
                class="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <button
                  @click.stop="editLibrary(library)"
                  :disabled="loading"
                  class="text-gray-400 hover:text-gray-900 p-1 rounded transition-colors disabled:opacity-50"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
                <button
                  @click.stop="deleteLibrary(library.id)"
                  :disabled="loading"
                  class="text-gray-400 hover:text-red-500 p-1 rounded transition-colors disabled:opacity-50"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="flex-1 flex flex-col">
      <!-- 文档库详情头部 -->
      <div
        class="bg-white/80 backdrop-blur-sm border-b border-gray-100 p-4 shadow-sm"
        v-if="selectedLibrary"
      >
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-normal text-gray-900">
              {{ selectedLibrary.title }}
            </h2>
            <p class="text-sm text-gray-600 mt-1 font-light">
              {{ selectedLibrary.description || "暂无描述" }}
            </p>
          </div>
          <div class="flex space-x-3">
            <button
              @click="viewKnowledgeGraph"
              :disabled="loading"
              class="bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg
                class="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                />
              </svg>
              知识图谱
            </button>
            <button
              @click="showAddDocumentDialog = true"
              :disabled="loading"
              class="bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg
                class="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 4v16m8-8H4"
                />
              </svg>
              添加文档
            </button>
          </div>
        </div>
      </div>

      <!-- 文档列表 -->
      <div class="flex-1 overflow-y-auto p-4" v-if="selectedLibrary">
        <!-- 文档加载状态 -->
        <div
          v-if="documentLoading"
          class="flex items-center justify-center py-8"
        >
          <div
            class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"
          ></div>
          <span class="ml-2 text-gray-600 font-light">加载文档中...</span>
        </div>

        <!-- 文档列表 -->
        <div
          v-else-if="
            selectedLibrary.documents && selectedLibrary.documents.length > 0
          "
          class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
            <div
            v-for="document in selectedLibrary.documents"
            :key="document.id"
            class="bg-white rounded-lg border border-gray-100 p-4 hover:shadow-sm transition-shadow group relative"
          >
            <!-- 删除按钮固定在右上角 -->
            <button
              @click="removeDocument(document.id)"
              :disabled="loading"
              class="absolute top-2 right-2 text-gray-400 hover:text-red-500 p-1.5 rounded-lg hover:bg-red-50 transition-all disabled:opacity-50 z-10"
              title="删除文档"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>

            <div class="flex items-start pr-8">
              <div class="flex items-center flex-1 min-w-0">
                <div
                  class="w-8 h-8 rounded-lg flex items-center justify-center mr-3 flex-shrink-0"
                  :class="getDocumentTypeClass(document.type)"
                >
                  <svg
                    v-if="document.type === 'link'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.1m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                    />
                  </svg>
                  <svg
                    v-else
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <h4 class="text-sm font-normal text-gray-900 truncate" :title="document.name">
                    {{ document.name }}
                  </h4>
                  <p class="text-xs text-gray-500 font-light">
                    {{ document.type === "link" ? "网站链接" : "文件" }}
                  </p>
                </div>
              </div>
            </div>

            <div v-if="document.url" class="text-xs text-gray-700 truncate mt-2" :title="document.url">
              <a :href="document.url" target="_blank" class="hover:underline">
                {{ document.url }}
              </a>
            </div>

            <!-- 解析状态徽章 (PR-3) -->
            <div class="flex items-center justify-between mt-3">
              <div class="flex items-center space-x-2">
                <!-- 状态徽章 -->
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  :class="getParseStatusClass(document.parse_status)"
                >
                  <span 
                    v-if="document.parse_status === 'processing'" 
                    class="animate-spin mr-1 w-3 h-3 border-2 border-current border-t-transparent rounded-full"
                  ></span>
                  {{ getParseStatusText(document.parse_status) }}
                </span>
                
                <!-- 重试按钮 (仅失败状态显示) -->
                <button
                  v-if="document.parse_status === 'failed'"
                  @click="retryDocumentProcess(document.id)"
                  :disabled="loading"
                  class="inline-flex items-center px-2 py-0.5 text-xs text-orange-600 hover:text-orange-800 hover:bg-orange-50 rounded transition-colors disabled:opacity-50"
                  title="重新处理"
                >
                  <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  重试
                </button>
                
                <!-- 处理按钮 (pending 或 未知状态显示) -->
                <button
                  v-if="!document.parse_status || document.parse_status === 'pending'"
                  @click="triggerDocumentProcess(document.id)"
                  :disabled="loading"
                  class="inline-flex items-center px-2 py-0.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                  title="开始处理"
                >
                  <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  处理
                </button>
              </div>
              
              <div class="text-xs text-gray-400 font-light">
                {{ formatTime(document.created_at) }}
              </div>
            </div>
            
            <!-- 错误信息提示 (仅失败状态显示) -->
            <div 
              v-if="document.parse_status === 'failed' && document.parse_error"
              class="mt-2 text-xs text-red-500 bg-red-50 rounded px-2 py-1 truncate"
              :title="document.parse_error"
            >
              {{ document.parse_error }}
            </div>
          </div>
        </div>

        <!-- 空文档状态 -->
        <div v-else class="text-center py-12 text-gray-500">
          <svg
            class="w-16 h-16 mx-auto mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p class="text-lg mb-2 font-normal">暂无文档</p>
          <p class="text-sm font-light">点击右上角按钮添加第一个文档</p>
        </div>
      </div>

      <!-- 未选择文档库状态 -->
      <div v-else class="flex-1 flex items-center justify-center text-gray-500">
        <div class="text-center">
          <svg
            class="w-20 h-20 mx-auto mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p class="text-lg mb-2 font-normal">选择一个文档库</p>
          <p class="text-sm font-light">
            从左侧列表中选择文档库来查看和管理文档
          </p>
        </div>
      </div>
    </div>

    <!-- 创建/编辑文档库对话框 -->
    <div
      v-if="showCreateDialog || showEditDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.12)] border border-gray-100 p-6 w-full max-w-md mx-4"
      >
        <h3 class="text-lg font-normal text-gray-900 mb-4">
          {{ showEditDialog ? "编辑文档库" : "创建文档库" }}
        </h3>
        <form
          @submit.prevent="showEditDialog ? updateLibrary() : createLibrary()"
        >
          <div class="mb-4">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >标题</label
            >
            <input
              v-model="libraryForm.title"
              type="text"
              required
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="请输入文档库标题"
            />
          </div>
          <div class="mb-6">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >描述</label
            >
            <textarea
              v-model="libraryForm.description"
              rows="3"
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="请输入文档库描述（可选）"
            ></textarea>
          </div>
          <div v-if="!showEditDialog" class="mb-6">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >校验码</label
            >
            <input
              v-model="libraryForm.verificationCode"
              type="text"
              required
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="请输入校验码"
            />
          </div>
          <div class="flex justify-end space-x-3">
            <button
              type="button"
              @click="closeDialog"
              :disabled="loading"
              class="px-4 py-2 text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 hover:border-gray-300 transition-colors disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="loading"
              class="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center"
            >
              <div
                v-if="loading"
                class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"
              ></div>
              {{ showEditDialog ? "更新" : "创建" }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 添加文档对话框 -->
    <div
      v-if="showAddDocumentDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.12)] border border-gray-100 p-6 w-full max-w-md mx-4"
      >
        <h3 class="text-lg font-normal text-gray-900 mb-4">添加文档</h3>
        <form @submit.prevent="addDocument">
          <div class="mb-4">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >文档类型</label
            >
            <select
              v-model="documentForm.type"
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
            >
              <option value="link">网站链接</option>
              <option value="file">文件上传</option>
            </select>
          </div>

          <div v-if="documentForm.type === 'link'" class="mb-4">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >链接地址</label
            >
            <input
              v-model="documentForm.url"
              type="url"
              required
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="https://example.com"
            />
          </div>

          <div v-if="documentForm.type === 'link'" class="mb-4">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >URL前缀限制</label
            >
            <input
              v-model="documentForm.prefix"
              type="text"
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="留空则自动使用URL根路径"
            />
            <p class="text-xs text-gray-500 mt-1 font-light">
              只爬取以此前缀开头的URL，留空则自动使用输入URL的根路径
            </p>
          </div>

          <div v-if="documentForm.type === 'file'" class="mb-4">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >选择文件</label
            >
            <input
              @change="handleFileSelect"
              type="file"
              accept=".pdf,.doc,.docx,.md,.txt"
              multiple
              required
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
            />
            <p class="text-xs text-gray-500 mt-1 font-light">
              支持 PDF、DOC、DOCX、MD、TXT 格式，可选择多个文件
            </p>
            <!-- 显示已选择的文件列表 -->
            <div v-if="documentForm.files && documentForm.files.length > 0" class="mt-2 space-y-1">
              <div v-for="(file, index) in documentForm.files" :key="index" class="flex items-center justify-between text-sm text-gray-600 bg-gray-50 rounded px-2 py-1">
                <span class="truncate">{{ file.name }}</span>
                <button @click="removeFile(index)" type="button" class="text-red-400 hover:text-red-600 ml-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div v-if="documentForm.type === 'link'" class="mb-6">
            <label class="block text-sm font-normal text-gray-700 mb-2"
              >文档名称</label
            >
            <input
              v-model="documentForm.name"
              type="text"
              required
              :disabled="loading"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
              placeholder="请输入文档名称"
            />
          </div>

          <div class="flex justify-end space-x-3">
            <button
              type="button"
              @click="showAddDocumentDialog = false"
              :disabled="loading"
              class="px-4 py-2 text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 hover:border-gray-300 transition-colors disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="loading"
              class="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center"
            >
              <div
                v-if="loading"
                class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"
              ></div>
              添加
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessageBox, ElMessage } from "element-plus";
import { knowledgeAPI } from "@/api/knowledge.js";
const FRONTEND_VERIFY_CODE = import.meta.env.VITE_KB_VERIFY_CODE || "123456";

// 路由
const router = useRouter();

// 响应式数据
const documentLibraries = ref([]);
const selectedLibrary = ref(null);
const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const showAddDocumentDialog = ref(false);
const loading = ref(false);
const documentLoading = ref(false);
const error = ref("");
const isCrawling = ref(false);  // 爬取中状态，防止并发上传

// 表单数据
const libraryForm = reactive({
  title: "",
  description: "",
  verificationCode: "",
});

const documentForm = reactive({
  type: "link",
  name: "",
  url: "",
  prefix: "",
  files: [],  // 改为数组，支持多文件
  content: "",
});

// 加载知识库列表
const loadLibraries = async () => {
  try {
    loading.value = true;
    error.value = "";
    const response = await knowledgeAPI.getLibraries();

    if (response.status === 200) {
      documentLibraries.value = response.data || [];
    } else {
      throw new Error(response.msg || "获取知识库列表失败");
    }
  } catch (err) {
    console.error("加载知识库列表失败:", err);
    error.value = err.message || "加载知识库列表失败";
    ElMessage.error(error.value);
  } finally {
    loading.value = false;
  }
};

// 选择知识库并加载详情
const selectLibrary = async (library) => {
  try {
    selectedLibrary.value = library;
    documentLoading.value = true;

    const response = await knowledgeAPI.getLibraryDetail(library.id);
    if (response.status === 200) {
      selectedLibrary.value = response.data;
    } else {
      throw new Error(response.msg || "获取知识库详情失败");
    }
  } catch (err) {
    console.error("加载知识库详情失败:", err);
    ElMessage.error(err.message || "加载知识库详情失败");
  } finally {
    documentLoading.value = false;
  }
};

// 创建知识库
const createLibrary = async () => {
  try {
    if (!libraryForm.verificationCode) {
      ElMessage.error("请输入校验码");
      return;
    }
    if (libraryForm.verificationCode !== FRONTEND_VERIFY_CODE) {
      ElMessage.error("校验码错误");
      return;
    }
    loading.value = true;
    const response = await knowledgeAPI.createLibrary({
      title: libraryForm.title,
      description: libraryForm.description,
    });

    if (response.status === 200) {
      ElMessage.success("文档库创建成功");
      closeDialog();
      await loadLibraries();
    } else {
      throw new Error(response.msg || "创建文档库失败");
    }
  } catch (err) {
    if (err === "cancel") {
      return;
    }
    console.error("创建知识库失败:", err);
    ElMessage.error(err.message || "创建文档库失败");
  } finally {
    loading.value = false;
  }
};

// 编辑知识库
const editLibrary = (library) => {
  libraryForm.title = library.title;
  libraryForm.description = library.description;
  selectedLibrary.value = library;
  showEditDialog.value = true;
};

// 更新知识库
const updateLibrary = async () => {
  try {
    loading.value = true;
    const response = await knowledgeAPI.updateLibrary(
      selectedLibrary.value.id,
      {
        title: libraryForm.title,
        description: libraryForm.description,
      }
    );

    if (response.status === 200) {
      ElMessage.success("文档库更新成功");
      closeDialog();
      await loadLibraries();
      // 如果当前选中的是被更新的库，重新加载详情
      if (selectedLibrary.value) {
        await selectLibrary(selectedLibrary.value);
      }
    } else {
      throw new Error(response.msg || "更新文档库失败");
    }
  } catch (err) {
    console.error("更新知识库失败:", err);
    ElMessage.error(err.message || "更新文档库失败");
  } finally {
    loading.value = false;
  }
};

// 删除知识库
const deleteLibrary = async (libraryId) => {
  try {
    await ElMessageBox.confirm(
      "确定要删除这个文档库吗？删除后无法恢复。",
      "删除确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    loading.value = true;
    const response = await knowledgeAPI.deleteLibrary(libraryId);

    if (response.status === 200) {
      ElMessage.success("文档库删除成功");
      if (selectedLibrary.value?.id === libraryId) {
        selectedLibrary.value = null;
      }
      await loadLibraries();
    } else {
      throw new Error(response.msg || "删除文档库失败");
    }
  } catch (err) {
    if (err !== "cancel") {
      console.error("删除知识库失败:", err);
      ElMessage.error(err.message || "删除文档库失败");
    }
  } finally {
    loading.value = false;
  }
};

// 添加文档
const addDocument = async () => {
  try {
    if (!selectedLibrary.value) return;

    loading.value = true;

    // 如果是网站链接类型，使用爬取接口
    if (documentForm.type === "link" && documentForm.url) {
      try {
        // 检查是否正在爬取中
        if (isCrawling.value) {
          ElMessage.warning("后台正在处理上一个链接，请等待完成后再添加");
          loading.value = false;
          return;
        }

        // 检查重复链接
        const existingDoc = selectedLibrary.value.documents?.find(
          (doc) => doc.url === documentForm.url
        );
        if (existingDoc) {
          ElMessage.error(`链接已存在：${existingDoc.name}`);
          loading.value = false;
          return;
        }

        // 设置爬取中状态
        isCrawling.value = true;

        // 计算prefix：如果用户没有填写，则使用URL最后一个斜杠及之前的内容
        let prefix = documentForm.prefix;
        if (!prefix) {
          const url = new URL(documentForm.url);
          const pathname = url.pathname;
          const lastSlashIndex = pathname.lastIndexOf("/");
          if (lastSlashIndex > 0) {
            prefix = url.origin + pathname.substring(0, lastSlashIndex + 1);
          } else {
            prefix = url.origin + "/";
          }
        }

        const crawlData = {
          url: documentForm.url,
          prefix: prefix,
          title: documentForm.name,
          collection_id: selectedLibrary.value.collection_id,
          user_id: "default_user", // 可以根据实际情况设置用户ID
          if_llm: false, // 可以根据需要设置是否使用LLM
        };

        const crawlResponse = await knowledgeAPI.crawlSite(crawlData);

        if (crawlResponse.status === 200) {
          ElMessage.success("网站爬取任务已启动，正在后台处理...");
          resetDocumentForm();
          showAddDocumentDialog.value = false;
          // 重新加载当前知识库详情
          await selectLibrary(selectedLibrary.value);
          // 延迟解除爬取锁定（给后台一些时间开始处理）
          setTimeout(() => {
            isCrawling.value = false;
          }, 3000);
          return;
        } else {
          isCrawling.value = false;
          throw new Error(crawlResponse.msg || "网站爬取失败");
        }
      } catch (crawlError) {
        isCrawling.value = false;
        console.error("网站爬取失败:", crawlError);
        ElMessage.error("网站爬取失败: " + crawlError.message);
        return;
      }
    }

    // 原有的文档添加逻辑（用于文件上传）
    // 如果是文件上传类型，循环上传每个文件
    if (documentForm.type === "file" && documentForm.files && documentForm.files.length > 0) {
      const totalFiles = documentForm.files.length;
      let successCount = 0;
      let failCount = 0;
      
      for (let i = 0; i < documentForm.files.length; i++) {
        const file = documentForm.files[i];
        try {
          // 1. 获取OSS上传签名URL
          const uploadResponse = await knowledgeAPI.getUploadUrl(file.name);

          if (uploadResponse.status !== 200 || !uploadResponse.data) {
            throw new Error("获取上传URL失败");
          }

          // 2. 上传文件到OSS
          await knowledgeAPI.uploadFileToOSS(uploadResponse.data, file);

          // 3. 添加文档记录
          const documentData = {
            library_id: selectedLibrary.value.id,
            name: file.name,
            type: "file",
            content: "",
            url: uploadResponse.data.split("?")[0], // 去掉签名参数
          };
          
          const response = await knowledgeAPI.addDocument(documentData);
          if (response.status === 200) {
            successCount++;
          } else {
            failCount++;
          }
        } catch (uploadError) {
          console.error(`文件 ${file.name} 上传失败:`, uploadError);
          failCount++;
        }
      }
      
      // 显示上传结果
      if (successCount > 0) {
        ElMessage.success(`成功上传 ${successCount}/${totalFiles} 个文件`);
      }
      if (failCount > 0) {
        ElMessage.warning(`${failCount} 个文件上传失败`);
      }
      
      resetDocumentForm();
      showAddDocumentDialog.value = false;
      // 重新加载当前知识库详情
      await selectLibrary(selectedLibrary.value);
      return;
    }
    
    // 对于链接类型，保持原有逻辑
    let documentData = {
      library_id: selectedLibrary.value.id,
      name: documentForm.name,
      type: documentForm.type,
      content: documentForm.content || "",
      url: documentForm.url || "",
    };

    const response = await knowledgeAPI.addDocument(documentData);

    if (response.status === 200) {
      ElMessage.success("文档添加成功");
      resetDocumentForm();
      showAddDocumentDialog.value = false;
      // 重新加载当前知识库详情
      await selectLibrary(selectedLibrary.value);
    } else {
      throw new Error(response.msg || "添加文档失败");
    }
  } catch (err) {
    console.error("添加文档失败:", err);
    ElMessage.error(err.message || "添加文档失败");
  } finally {
    loading.value = false;
  }
};

// 查看知识图谱
const viewKnowledgeGraph = () => {
  if (selectedLibrary.value) {
    router.push({
      name: "knowledge-graph",
      params: { collection_id: selectedLibrary.value.collection_id },
    });
  }
};

// 删除文档
const removeDocument = async (documentId) => {
  try {
    await ElMessageBox.confirm("确定要移除这个文档吗？", "移除确认", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    loading.value = true;
    const response = await knowledgeAPI.deleteDocument(documentId);

    if (response.status === 200) {
      ElMessage.success("文档移除成功");
      // 重新加载当前知识库详情
      await selectLibrary(selectedLibrary.value);
    } else {
      throw new Error(response.msg || "移除文档失败");
    }
  } catch (err) {
    if (err !== "cancel") {
      console.error("删除文档失败:", err);
      ElMessage.error(err.message || "移除文档失败");
    }
  } finally {
    loading.value = false;
  }
};

// 处理文件选择（支持多文件）
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    // 追加到已选择的文件列表
    documentForm.files = [...documentForm.files, ...files];
  }
};

// 移除已选择的文件
const removeFile = (index) => {
  documentForm.files.splice(index, 1);
};

// 重置文档表单
const resetDocumentForm = () => {
  documentForm.name = "";
  documentForm.url = "";
  documentForm.prefix = "";
  documentForm.files = [];
  documentForm.content = "";
  documentForm.type = "link";
};

// 关闭对话框
const closeDialog = () => {
  showCreateDialog.value = false;
  showEditDialog.value = false;
  libraryForm.title = "";
  libraryForm.description = "";
  libraryForm.verificationCode = "";
};

// 获取文档类型样式
const getDocumentTypeClass = (type) => {
  switch (type) {
    case "pdf":
      return "bg-red-100 text-red-600";
    case "link":
      return "bg-blue-100 text-blue-600";
    case "file":
      return "bg-green-100 text-green-600";
    default:
      return "bg-gray-100 text-gray-600";
  }
};

// 格式化时间
const formatTime = (date) => {
  if (!date) return "";
  const now = new Date();
  const targetDate = new Date(date);
  const diffInHours = (now - targetDate) / (1000 * 60 * 60);

  if (diffInHours < 1) {
    return "刚刚";
  } else if (diffInHours < 24) {
    return `${Math.floor(diffInHours)}小时前`;
  } else {
    return targetDate.toLocaleDateString("zh-CN");
  }
};

// ==================== 文档处理相关函数 (PR-3) ====================

// 获取解析状态样式类
const getParseStatusClass = (status) => {
  switch (status) {
    case "pending":
      return "bg-gray-100 text-gray-600";
    case "processing":
      return "bg-blue-100 text-blue-600";
    case "completed":
      return "bg-green-100 text-green-600";
    case "failed":
      return "bg-red-100 text-red-600";
    default:
      return "bg-gray-100 text-gray-600";
  }
};

// 获取解析状态文本
const getParseStatusText = (status) => {
  switch (status) {
    case "pending":
      return "待处理";
    case "processing":
      return "处理中";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return "未知";
  }
};

// 触发文档处理
const triggerDocumentProcess = async (documentId) => {
  try {
    loading.value = true;
    const response = await knowledgeAPI.processDocument(documentId);
    
    if (response.status === 200) {
      ElMessage.success("文档处理已启动");
      // 刷新文档列表以显示新状态
      await selectLibrary(selectedLibrary.value);
    } else {
      throw new Error(response.msg || "触发处理失败");
    }
  } catch (err) {
    console.error("触发文档处理失败:", err);
    ElMessage.error(err.message || "触发处理失败");
  } finally {
    loading.value = false;
  }
};

// 重试文档处理
const retryDocumentProcess = async (documentId) => {
  try {
    loading.value = true;
    const response = await knowledgeAPI.retryDocument(documentId);
    
    if (response.status === 200) {
      ElMessage.success("文档重试处理已启动");
      // 刷新文档列表以显示新状态
      await selectLibrary(selectedLibrary.value);
    } else {
      throw new Error(response.msg || "重试处理失败");
    }
  } catch (err) {
    console.error("重试文档处理失败:", err);
    ElMessage.error(err.message || "重试处理失败");
  } finally {
    loading.value = false;
  }
};

// 轮询定时器
let pollTimer = null;

// 开始轮询状态
const startPolling = () => {
  if (pollTimer) return;
  
  pollTimer = setInterval(async () => {
    // 只有在当前有选中的文档库且有正在处理的文档时才刷新
    if (selectedLibrary.value && selectedLibrary.value.documents) {
      const hasProcessing = selectedLibrary.value.documents.some(
        doc => doc.parse_status === 'processing' || doc.parse_status === 'pending'
      );
      
      if (hasProcessing) {
        // 静默刷新（不显示 loading）
        try {
          const response = await knowledgeAPI.getLibraryDetail(selectedLibrary.value.id);
          if (response.status === 200) {
            // 更新文档列表，保留其他状态
            selectedLibrary.value = response.data;
          }
        } catch (e) {
          console.error("轮询刷新失败:", e);
        }
      } else {
        // 如果没有处理中的文档，停止轮询
        stopPolling();
      }
    } else {
      stopPolling();
    }
  }, 3000); // 每3秒刷新一次
};

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

// 监听 selectLibrary 的完成，如果有处理中的文档则启动轮询
const originalSelectLibrary = selectLibrary;
// 已经在上面定义了 selectLibrary，这里需要修改它或者在它调用的地方插入逻辑
// 由于 selectLibrary 是 const 定义的，我不能重新赋值。
// 我应该在 selectLibrary 的 finally 块或者成功回调里调用 startPolling
// 但为了改动最小，我可以利用 watch 或者在 onMounted 里做。

import { onUnmounted, watch } from "vue";

// 监听 selectedLibrary 变化来启动轮询
watch(() => selectedLibrary.value, (newVal) => {
  if (newVal && newVal.documents) {
    const hasProcessing = newVal.documents.some(
      doc => doc.parse_status === 'processing' || doc.parse_status === 'pending'
    );
    if (hasProcessing) {
      startPolling();
    }
  }
}, { deep: true });

// 组件挂载时加载数据
onMounted(() => {
  loadLibraries();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
