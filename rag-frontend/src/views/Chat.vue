<template>
  <div class="h-screen flex bg-amber-50/30 overflow-hidden">
    <!-- 左侧边栏 -->
    <div 
      :class="[
        'bg-white border-r border-gray-100 flex flex-col shadow-sm transition-all duration-300 relative',
        sidebarCollapsed ? 'w-16' : 'w-80'
      ]"
    >
      <!-- 折叠/展开按钮 -->
      <button
        @click="sidebarCollapsed = !sidebarCollapsed"
        class="absolute -right-3 top-6 z-20 w-6 h-6 bg-white border border-gray-200 rounded-full shadow-sm flex items-center justify-center hover:bg-gray-50 transition-colors"
        :title="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
      >
        <svg
          class="w-3 h-3 text-gray-600 transition-transform duration-300"
          :class="{ 'rotate-180': sidebarCollapsed }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>

      <!-- 头部 -->
      <div class="p-4 border-b border-gray-100">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center space-x-2">
            <div
              class="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center flex-shrink-0"
            >
              <svg
                class="w-4 h-4 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.959 8.959 0 01-4.906-1.471c-.905-.556-1.94-.808-3.094-.808-1.154 0-2.189.252-3.094.808A8.959 8.959 0 013 20c0-4.418 3.582-8 8-8s8 3.582 8 8z"
                />
              </svg>
            </div>
            <h1 v-if="!sidebarCollapsed" class="text-lg font-medium text-gray-900 whitespace-nowrap overflow-hidden">AdaptiMultiRAG</h1>
          </div>
          <button
            v-if="!sidebarCollapsed"
            @click="logout"
            class="text-gray-500 hover:text-gray-900 p-2 rounded-lg hover:bg-gray-50 transition-colors"
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
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
          </button>
        </div>
        <button
          @click="createNewConversation"
          :class="[
            'w-full bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center font-medium',
            sidebarCollapsed ? 'p-2.5' : 'py-2.5 px-4'
          ]"
          :title="sidebarCollapsed ? '新建对话' : ''"
        >
          <svg
            :class="sidebarCollapsed ? 'w-5 h-5' : 'w-4 h-4 mr-2'"
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
          <span v-if="!sidebarCollapsed">新建对话</span>
        </button>
      </div>

      <!-- 对话列表 -->
      <div class="flex-1 overflow-y-auto p-3">
        <div class="space-y-1">
          <div
            v-for="conversation in conversations"
            :key="conversation.id"
            @click="selectConversation(conversation.id)"
            class="p-3 rounded-lg cursor-pointer transition-all group"
            :class="{
              'bg-amber-50 border border-amber-200':
                currentConversation?.id === conversation.id,
              'hover:bg-gray-50 border border-transparent':
                currentConversation?.id !== conversation.id,
            }"
            :title="sidebarCollapsed ? conversation.title : ''"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <!-- 折叠时显示对话图标 -->
                <div v-if="sidebarCollapsed" class="flex justify-center">
                  <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <!-- 展开时显示标题 -->
                <h3 v-else class="text-sm font-normal text-gray-900 truncate">
                  {{ conversation.title }}
                </h3>
              </div>
              <button
                v-if="!sidebarCollapsed"
                @click.stop="deleteConversation(conversation.id)"
                class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-900 p-1 rounded transition-all"
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

      <!-- 底部导航 -->
      <div class="p-4 border-t border-gray-100">
        <router-link
          to="/document-library"
          :class="[
            'block text-center text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors font-normal',
            sidebarCollapsed ? 'p-2' : 'py-2 px-3'
          ]"
          :title="sidebarCollapsed ? '文档库管理' : ''"
        >
          <svg v-if="sidebarCollapsed" class="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
          <span v-else>文档库管理</span>
        </router-link>
      </div>
    </div>


    <!-- 主聊天区域 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 聊天头部 -->
      <div
        class="bg-white/80 backdrop-blur-sm border-b border-gray-100 p-4 shadow-sm"
      >
        <h2 class="text-lg font-normal text-gray-900">
          {{ currentConversation?.title || "选择或创建一个对话" }}
        </h2>
      </div>

      <!-- 消息区域 -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messagesContainer">
        <!-- 加载状态 -->
        <div
          v-if="loading && currentConversation"
          class="flex items-center justify-center h-full"
        >
          <div class="text-center">
            <div class="relative inline-block">
              <!-- 背景圆环 -->
              <div
                class="w-12 h-12 rounded-full border-4 border-gray-200"
              ></div>
              <!-- 旋转的蓝色圆环 -->
              <div
                class="absolute inset-0 w-12 h-12 rounded-full border-4 border-transparent border-t-blue-600 animate-spin"
              ></div>
            </div>
            <p class="text-gray-500 mt-4 text-sm">正在加载对话内容...</p>
            <!-- 添加一些点动画 -->
            <div class="flex justify-center mt-2 space-x-1">
              <div
                class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
              ></div>
              <div
                class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                style="animation-delay: 0.1s"
              ></div>
              <div
                class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                style="animation-delay: 0.2s"
              ></div>
            </div>
          </div>
        </div>

        <div
          v-else-if="!currentConversation"
          class="flex items-center justify-center h-full"
        >
          <div class="text-center text-gray-500">
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
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.959 8.959 0 01-4.906-1.471c-.905-.556-1.94-.808-3.094-.808-1.154 0-2.189.252-3.094.808A8.959 8.959 0 013 20c0-4.418 3.582-8 8-8s8 3.582 8 8z"
              />
            </svg>
            <p class="text-lg font-medium mb-2">开始新的对话</p>
            <p class="text-sm">点击"新建对话"开始与AI助手聊天</p>
          </div>
        </div>

        <div
          v-else
          v-for="item in groupedMessages"
          :key="item.id"
          class="mb-4"
        >
          <!-- 用户消息 -->
          <template v-if="item.type === 'user'">
            <div class="flex gap-4 justify-end">
              <div
                class="px-4 py-2 rounded-lg bg-gray-900 text-white max-w-xs lg:max-w-md"
              >
                <p class="text-sm whitespace-pre-wrap">{{ item.message.content }}</p>
              </div>
            </div>
          </template>

          <!-- 对话轮次（包含 node_updates + assistant 答案） -->
          <template v-else-if="item.type === 'turn'">
            <!-- 节点更新消息折叠区（在答案上方） -->
            <div v-if="item.nodeUpdates.length > 0" class="mb-3">
              <div
                v-for="nodeUpdate in item.nodeUpdates"
                :key="nodeUpdate.id"
                class="w-full max-w-3xl"
              >
                <details class="node-update-details">
                  <summary class="node-update-summary">
                    <div class="node-update-caret">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                    <div class="node-update-title">
                      <p>{{ getNodeDisplayName(nodeUpdate.node_name) }}</p>
                    </div>
                  </summary>
                  <div class="node-update-content">
                    <div class="node-update-content-text">
                      {{ nodeUpdate.content }}
                    </div>
                  </div>
                </details>
              </div>
            </div>

            <!-- AI 助手答案 -->
            <div v-if="item.assistant" class="flex gap-4">
              <!-- 头像 -->
              <div class="flex-shrink-0">
                <div
                  class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center"
                >
                  <span class="text-sm font-semibold text-blue-600">AI</span>
                </div>
              </div>

              <!-- 消息内容 -->
              <div class="flex-1 max-w-3xl">
                <div
                  class="text-sm text-gray-700 prose prose-sm max-w-none"
                  v-html="renderMarkdown(item.assistant.content)"
                ></div>

                <!-- 操作按钮 -->
                <div class="flex items-center gap-2 mt-3">
                  <button
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="编辑"
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
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="复制"
                    @click="copyToClipboard(item.assistant.content)"
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
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="朗读"
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
                        d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="点赞"
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
                        d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="点踩"
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
                        d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-gray-600 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    title="重新生成"
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
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </template>
        </div>

      </div>

      <!-- 输入区域 -->
      <div class="bg-white border-t border-gray-100 p-4">
        <!-- 当前设置信息提示 -->
        <div class="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span class="text-gray-500 font-normal">当前设置:</span>
          <span
            class="px-2 py-1 bg-amber-50 text-gray-700 rounded border border-amber-200 font-light"
          >
            {{ getRagModeText(ragMode) }}
          </span>
          <span
            v-if="selectedLibrary"
            class="px-2 py-1 bg-blue-50 text-gray-700 rounded border border-blue-200 font-light"
          >
            📚 {{ getSelectedLibraryName(selectedLibrary) }}
          </span>
          <span
            v-else
            class="px-2 py-1 bg-gray-50 text-gray-500 rounded border border-gray-200 font-light"
          >
                      未选择知识库
          </span>
        </div>

        <!-- 文献快速选择标签 (只在知识库有效且有文献时显示) -->
        <div v-if="selectedLibrary && getSelectedLibraryName(selectedLibrary) !== '未知知识库' && selectedLibraryDocuments.length > 0" class="mb-3">
          <div class="flex items-start gap-2">
            <span class="text-xs text-gray-500 whitespace-nowrap pt-1">📄 插入文献:</span>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="doc in selectedLibraryDocuments"
                :key="doc.id"
                @click="insertDocumentName(doc.name)"
                type="button"
                class="px-2.5 py-1 text-xs bg-blue-50 text-blue-700 rounded-full 
                       hover:bg-blue-100 border border-blue-200 transition-colors
                       max-w-[200px] truncate"
                :title="doc.name"
              >
                {{ truncateText(doc.name, 25) }}
              </button>
            </div>
          </div>
        </div>

        <form @submit.prevent="sendMessage" class="flex space-x-4">
          <!-- 设置按钮 -->
          <button
            @click="openSettingsModal"
            type="button"
            class="bg-gray-50 text-gray-600 px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-100 hover:border-gray-300 focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 transition-colors"
            title="RAG设置"
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
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>

          <textarea
            ref="messageInputRef"
            v-model="newMessage"
            placeholder="输入您的消息..."
            rows="1"
            class="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent bg-white resize-none overflow-hidden min-h-[42px] max-h-[200px]"
            :disabled="streaming"
            @input="adjustTextareaHeight"
            @keydown="handleKeydown"
          ></textarea>
          <button
            type="submit"
            :disabled="!newMessage.trim() || streaming"
            class="bg-gray-900 text-white px-6 py-2 rounded-lg hover:bg-gray-800 focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </form>
      </div>
    </div>

    <!-- 右侧Agent架构图面板 -->
    <div
      :style="{ width: agentPanelWidth + 'px' }"
      class="bg-gradient-to-br from-amber-50/50 to-orange-50/50 border-l border-gray-100 flex flex-col overflow-hidden flex-shrink-0 relative"
    >
      <!-- 左侧拖动条 -->
      <div
        @mousedown="startResize"
        class="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-gray-300 transition-colors z-10 group"
        :class="{ 'bg-gray-400': isResizing }"
      >
        <!-- 可视化拖动指示器 -->
        <div
          class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-12 bg-gray-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
        ></div>
      </div>

      <!-- 面板头部 -->
      <div class="p-4 border-b border-gray-100">
        <h3 class="text-lg font-normal text-gray-900">Agent架构流程</h3>
        <p class="text-xs text-gray-500 mt-1 font-light">RAG智能体工作流程图</p>
      </div>

      <!-- Mermaid流程图 -->
      <div class="flex-1 overflow-y-auto p-4">
        <div class="mermaid-container" ref="mermaidContainer">
          <pre class="mermaid" id="agent-flowchart">
flowchart TD
    A(["开始"]) --> n2["是否需要检索"]
    B{"判断原始问题类型"} --> C["适合使用向量数据库"] & D["适合使用图数据库"]
    n1["由原始问题扩展子问题"] --> B
    n2 -- 是 --> n1
    n6["生成答案结点"] --> n3(["结束"])
    n2 -- 否 --> n7["直接回答"]
    n7 --> n3
    D --> n6
    C --> n6
          </pre>
        </div>

        <!-- 当前执行节点提示 -->
        <div
          v-if="currentExecutingNode"
          class="mt-4 p-3 bg-white/80 border border-gray-200 rounded-lg shadow-sm"
        >
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 bg-gray-900 rounded-full animate-pulse"></div>
            <span class="text-sm font-normal text-gray-900"
              >正在执行: {{ currentExecutingNode }}</span
            >
          </div>
        </div>
      </div>
    </div>

    <!-- 知识库选择提示弹窗 -->
    <BaseModal
      v-model="showLibrarySelectDialog"
      title="选择知识库"
      size="md"
      :close-on-click-outside="false"
    >
      <div class="space-y-4">
        <div
          class="flex items-start space-x-3 p-4 bg-amber-50 rounded-lg border border-amber-200"
        >
          <svg
            class="w-5 h-5 text-gray-700 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div class="text-sm text-gray-800">
            <p class="font-normal mb-1">提示</p>
            <p class="font-light">
              选择一个知识库以获得更准确的回答，或选择"不使用知识库"直接与AI对话。
            </p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-normal text-gray-700 mb-3"
            >请选择知识库</label
          >
          <div v-if="librariesLoading" class="text-center py-8">
            <div
              class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"
            ></div>
            <p class="text-sm text-gray-500 mt-3 font-light">
              正在加载知识库...
            </p>
          </div>
          <div
            v-else-if="knowledgeLibraries.length === 0"
            class="text-center py-8"
          >
            <EmptyState
              title="暂无知识库"
              description="您还没有创建任何知识库，请先到文档库管理页面创建。"
            >
              <template #action>
                <BaseButton variant="primary" @click="goToDocumentLibrary">
                  <template #icon>
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
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </template>
                  创建知识库
                </BaseButton>
              </template>
            </EmptyState>
          </div>
          <div v-else class="space-y-2 max-h-64 overflow-y-auto">
            <label
              class="flex items-center p-4 border-2 rounded-xl cursor-pointer hover:bg-amber-50/50 transition-all duration-200"
              :class="{
                'border-gray-900 bg-amber-50': selectedLibraryForDialog === '',
                'border-gray-200': selectedLibraryForDialog !== '',
              }"
            >
              <input
                type="radio"
                value=""
                v-model="selectedLibraryForDialog"
                class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 focus:ring-gray-900 focus:ring-2"
              />
              <div class="ml-3">
                <div class="text-sm font-normal text-gray-900">
                  不使用知识库
                </div>
                <div class="text-xs text-gray-500 font-light">
                  仅使用基础AI模型回答
                </div>
              </div>
            </label>
            <label
              v-for="library in knowledgeLibraries"
              :key="library.id"
              class="flex items-center p-4 border-2 rounded-xl cursor-pointer hover:bg-amber-50/50 transition-all duration-200"
              :class="{
                'border-gray-900 bg-amber-50':
                  selectedLibraryForDialog === library.id,
                'border-gray-200': selectedLibraryForDialog !== library.id,
              }"
            >
              <input
                type="radio"
                :value="library.id"
                v-model="selectedLibraryForDialog"
                class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 focus:ring-gray-900 focus:ring-2"
              />
              <div class="ml-3 flex-1">
                <div class="text-sm font-normal text-gray-900">
                  {{ library.title }}
                </div>
                <div class="text-xs text-gray-500 font-light">
                  {{ library.description || "暂无描述" }}
                </div>
              </div>
              <span v-if="library.document_count" class="badge badge-primary">
                {{ library.document_count }} 个文档
              </span>
            </label>
          </div>
        </div>

        <div class="flex items-center space-x-2 text-xs text-gray-500">
          <input
            type="checkbox"
            id="dontShowAgain"
            v-model="dontShowLibrarySelectAgain"
            class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 rounded focus:ring-gray-900 focus:ring-2"
          />
          <label for="dontShowAgain" class="cursor-pointer font-light"
            >不再显示此提示</label
          >
        </div>
      </div>

      <template #footer>
        <BaseButton variant="secondary" @click="skipLibrarySelection">
          跳过
        </BaseButton>
        <BaseButton variant="primary" @click="confirmLibrarySelection">
          确认选择
        </BaseButton>
      </template>
    </BaseModal>

    <!-- 设置弹窗 -->
    <div
      v-if="settingsModalOpen"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click="cancelSettingsModal"
    >
      <div
        class="bg-white rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.12)] border border-gray-100 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        @click.stop
      >
        <!-- 弹窗头部 -->
        <div
          class="flex items-center justify-between p-6 border-b border-gray-100"
        >
          <h3 class="text-lg font-normal text-gray-900">
            {{
              isSettingsForConversationSwitch ? "切换对话前请先设置" : "RAG设置"
            }}
          </h3>
          <button
            @click="cancelSettingsModal"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- 弹窗内容 -->
        <div class="p-6 space-y-6">
          <!-- RAG模式选择 -->
          <div>
            <label class="block text-sm font-normal text-gray-700 mb-3"
              >RAG模式</label
            >
            <div class="space-y-2">
              <label
                v-for="option in ragOptions"
                :key="option.value"
                class="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-amber-50/50 transition-colors"
                :class="{
                  'border-gray-900 bg-amber-50': ragMode === option.value,
                }"
              >
                <input
                  type="radio"
                  :value="option.value"
                  v-model="ragMode"
                  class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 focus:ring-gray-900 focus:ring-2"
                />
                <div class="ml-3">
                  <div class="text-sm font-normal text-gray-900">
                    {{ option.label }}
                  </div>
                  <div class="text-xs text-gray-500 font-light">
                    {{ getRagModeDescription(option.value) }}
                  </div>
                </div>
              </label>
            </div>
          </div>

          <!-- 知识库选择 -->
          <div>
            <label class="block text-sm font-normal text-gray-700 mb-3"
              >选择知识库</label
            >
            <div v-if="librariesLoading" class="text-center py-4">
              <div
                class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"
              ></div>
              <p class="text-sm text-gray-500 mt-2 font-light">
                正在加载知识库...
              </p>
            </div>
            <div
              v-else-if="knowledgeLibraries.length === 0"
              class="text-center py-4"
            >
              <p class="text-sm text-gray-500 font-light">暂无知识库</p>
            </div>
            <div v-else class="space-y-2 max-h-48 overflow-y-auto">
              <label
                class="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-amber-50/50 transition-colors"
                :class="{
                  'border-gray-900 bg-amber-50': selectedLibrary === '',
                }"
              >
                <input
                  type="radio"
                  value=""
                  v-model="selectedLibrary"
                  class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 focus:ring-gray-900 focus:ring-2"
                />
                <div class="ml-3">
                  <div class="text-sm font-normal text-gray-900">
                    不使用知识库
                  </div>
                  <div class="text-xs text-gray-500 font-light">
                    仅使用基础AI模型回答
                  </div>
                </div>
              </label>
              <label
                v-for="library in knowledgeLibraries"
                :key="library.id"
                class="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-amber-50/50 transition-colors"
                :class="{
                  'border-gray-900 bg-amber-50': selectedLibrary === library.id,
                }"
              >
                <input
                  type="radio"
                  :value="library.id"
                  v-model="selectedLibrary"
                  class="w-4 h-4 text-gray-900 bg-gray-100 border-gray-300 focus:ring-gray-900 focus:ring-2"
                />
                <div class="ml-3">
                  <div class="text-sm font-normal text-gray-900">
                    {{ library.title }}
                  </div>
                  <div class="text-xs text-gray-500 font-light">
                    {{ library.description || "暂无描述" }}
                  </div>
                </div>
              </label>
            </div>
          </div>

          <!-- 高级设置 -->
          <div class="border-t border-gray-100 pt-6">
            <h4 class="text-sm font-normal text-gray-700 mb-4">高级设置</h4>

            <!-- 最大检索文档数量 -->
            <div class="mb-4">
              <label class="block text-sm font-normal text-gray-700 mb-2">
                最大检索文档数量: {{ maxRetrievalDocs }}
              </label>
              <input
                v-model.number="maxRetrievalDocs"
                type="range"
                min="1"
                max="10"
                class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <div
                class="flex justify-between text-xs text-gray-500 mt-1 font-light"
              >
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            <!-- 系统提示词 -->
            <div>
              <label class="block text-sm font-normal text-gray-700 mb-2"
                >系统提示词</label
              >
              <textarea
                v-model="systemPrompt"
                rows="4"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent resize-none bg-white"
                placeholder="你是一个专业的RAG助手，能够基于检索到的信息提供准确的回答。"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div
          class="flex items-center justify-end space-x-3 p-6 border-t border-gray-100"
        >
          <button
            v-if="isSettingsForConversationSwitch"
            @click="cancelSettingsModal"
            class="px-4 py-2 text-sm font-normal text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            取消
          </button>
          <button
            v-if="!isSettingsForConversationSwitch"
            @click="resetSettings"
            class="px-4 py-2 text-sm font-normal text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900"
          >
            重置默认
          </button>
          <button
            @click="closeSettingsModal"
            class="px-4 py-2 text-sm font-normal text-white bg-gray-900 border border-transparent rounded-lg hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900"
          >
            确定
          </button>
        </div>
      </div>
    </div>

    <!-- PR-2 阶段D改造: 证据片段抽屉 - 精确片段展示 -->
    <div
      v-if="evidenceDrawerVisible"
      class="fixed inset-0 bg-black bg-opacity-50 flex justify-end z-50"
      @click="evidenceDrawerVisible = false"
    >
      <div
        :style="{ width: evidenceDrawerWidth + 'px' }"
        class="bg-white h-full overflow-y-auto shadow-xl relative flex-shrink-0"
        @click.stop
      >
        <div
          @mousedown="startEvidenceResize"
          class="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-gray-300 transition-colors z-20 group"
          :class="{ 'bg-gray-400': isEvidenceResizing }"
        >
          <div
            class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-12 bg-gray-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
          ></div>
        </div>
        <!-- 抽屉头部 -->
        <div class="sticky top-0 bg-white border-b border-gray-200 p-4 z-10">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-medium text-gray-900">引用原文</h3>
              <span
                v-if="currentEvidenceDoc?.snippetId"
                class="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium"
              >
                {{ currentEvidenceDoc.snippetId }}
              </span>
            </div>
            <button
              @click="evidenceDrawerVisible = false"
              class="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 文献信息 -->
        <div class="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <div class="flex items-start gap-3">
            <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <h4 class="text-base font-medium text-gray-900 leading-tight">
                {{ currentEvidenceDoc?.title || currentEvidenceDoc?.name }}
              </h4>
              <div class="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
                <span v-if="currentEvidenceDoc?.authors?.length" class="flex items-center gap-1">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {{ currentEvidenceDoc.authors.slice(0, 2).join(', ') }}{{ currentEvidenceDoc.authors.length > 2 ? ' 等' : '' }}
                </span>
                <span v-if="currentEvidenceDoc?.year" class="flex items-center gap-1">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {{ currentEvidenceDoc.year }}年
                </span>
              </div>
              <div v-if="currentEvidenceDoc?.doi" class="mt-2">
                <a
                  :href="`https://doi.org/${currentEvidenceDoc.doi}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  DOI: {{ currentEvidenceDoc.doi }}
                </a>
              </div>
            </div>
          </div>
        </div>

        <!-- 精确证据片段 -->
        <div class="p-4">
          <!-- 精确模式标题（单个片段） -->
          <div v-if="currentEvidenceDoc?.snippetId" class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h5 class="text-sm font-medium text-gray-700">
              该引用对应的原文片段
            </h5>
          </div>
          <!-- 多片段模式标题 -->
          <div v-else class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <h5 class="text-sm font-medium text-gray-700">
              检索到的相关文段 ({{ currentEvidenceSnippets.length }})
            </h5>
          </div>

          <div v-if="currentEvidenceSnippets.length > 0" class="space-y-3">
            <div
              v-for="(snippet, index) in currentEvidenceSnippets"
              :key="snippet.id || index"
              :class="[
                'border rounded-lg p-4 transition-colors',
                currentEvidenceDoc?.snippetId
                  ? 'bg-green-50 border-green-200'
                  : 'bg-gray-50 border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'
              ]"
            >
              <div class="flex items-start gap-3">
                <span
                  :class="[
                    'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                    currentEvidenceDoc?.snippetId
                      ? 'bg-green-100 text-green-700'
                      : 'bg-amber-100 text-amber-700'
                  ]"
                >
                  {{ getEvidenceSnippetBadge(snippet, index) }}
                </span>
                <div class="flex-1 min-w-0">
                  <p
                    v-if="snippet.label"
                    class="text-xs font-semibold tracking-wide uppercase text-gray-500 mb-2"
                  >
                    {{ snippet.label }}
                  </p>
                  <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{{ snippet.text }}</p>
                  <div
                    v-if="snippet.context && snippet.context !== snippet.text"
                    class="mt-3 p-3 rounded-lg border border-gray-200 bg-white/80"
                  >
                    <p class="text-xs font-medium text-gray-500 mb-1">相邻上下文</p>
                    <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ snippet.context }}</p>
                  </div>
                  <p
                    v-if="snippet.cleaned"
                    class="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2.5 py-1.5 inline-block"
                  >
                    已自动去除封面标题、作者与机构等元数据噪声
                  </p>
                </div>
              </div>
            </div>

            <!-- 查看更多上下文按钮 -->
            <div v-if="currentEvidenceFullContent && currentEvidenceFullContent !== (currentEvidenceSnippets[0]?.context || currentEvidenceSnippets[0]?.text || '')" class="mt-3">
              <button
                @click="evidenceExpandedContext = !evidenceExpandedContext"
                class="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 transition-colors font-medium"
              >
                <svg class="w-3.5 h-3.5 transition-transform" :class="{ 'rotate-90': evidenceExpandedContext }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
                {{ evidenceExpandedContext ? '收起完整上下文' : '查看完整上下文' }}
              </button>
              <div
                v-if="evidenceExpandedContext"
                class="mt-2 p-4 bg-gray-50 border border-gray-200 rounded-lg"
              >
                <p class="text-xs text-gray-500 mb-2 font-medium">原始检索片段：</p>
                <p class="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{{ currentEvidenceFullContent }}</p>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-8 text-gray-500">
            <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-sm">暂无检索到的文段</p>
            <p class="text-xs mt-1">该引用可能来自图检索或其他来源</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessageBox, ElMessage } from "element-plus";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";
import { knowledgeAPI } from "../api/knowledge.js";
import MarkdownIt from "markdown-it";
import BaseModal from "@/components/BaseModal.vue";
import BaseButton from "@/components/BaseButton.vue";
import EmptyState from "@/components/EmptyState.vue";
import mermaid from "mermaid";
import texmath from "markdown-it-texmath";
import katex from "katex";
import "katex/dist/katex.min.css";

// 初始化markdown渲染器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
}).use(texmath, {
  engine: katex,
  delimiters: "dollars",  // 支持 $...$ 和 $$...$$ 语法
  katexOptions: { macros: { "\\RR": "\\mathbb{R}" } }
});

const router = useRouter();
const authStore = useAuthStore();
const chatStore = useChatStore();

const newMessage = ref("");
const messagesContainer = ref(null);
const messageInputRef = ref(null); // 输入框引用
const mermaidContainer = ref(null); // Mermaid容器引用
const sidebarCollapsed = ref(false); // 侧边栏折叠状态
const currentExecutingNode = ref(""); // 当前执行的节点
const ragMode = ref("auto"); // 改为单选
const selectedLibrary = ref(""); // 改为单选
const knowledgeLibraries = ref([]); // 知识库列表
const librariesLoading = ref(false); // 知识库加载状态
const selectedLibraryDocuments = ref([]); // 选中知识库的文献列表
const maxRetrievalDocs = ref(5); // 最大检索文档数量
const systemPrompt = ref(
  "你是一个专业的RAG助手，能够基于检索到的信息提供准确的回答。"
); // 系统提示词
const settingsModalOpen = ref(false); // 设置弹窗状态
const showLibrarySelectDialog = ref(false); // 知识库选择弹窗状态
const selectedLibraryForDialog = ref(""); // 弹窗中选择的知识库
const dontShowLibrarySelectAgain = ref(false); // 不再显示提示
const pendingConversationId = ref(null); // 待切换的对话ID（用于设置确认后切换）
const isSettingsForConversationSwitch = ref(false); // 标记设置对话框是否为切换对话触发

// Agent面板调整大小相关
const agentPanelWidth = ref(384); // 初始宽度 384px (w-96)
const isResizing = ref(false);
const startX = ref(0);
const startWidth = ref(0);
const evidenceDrawerWidth = ref(560);
const isEvidenceResizing = ref(false);
const evidenceStartX = ref(0);
const evidenceStartWidth = ref(0);

// 节点名称到流程图节点ID的映射
const nodeNameToId = {
  // 开始和结束节点
  start: "A", // 开始
  end: "n3", // 结束

  // 主流程节点
  route_question: "n2", // 是否需要检索
  check_retrieval_needed: "n2", // 是否需要检索(别名)

  // 检索分支
  query_expansion: "n1", // 由原始问题扩展子问题
  expand_subquestions: "n1", // 由原始问题扩展子问题(别名)

  classify_question: "B", // 判断原始问题类型
  classify_question_type: "B", // 判断原始问题类型(别名)

  retrieve_from_vector: "C", // 适合使用向量数据库
  vector_db_retrieval: "C", // 向量数据库检索(别名)

  retrieve_from_graph: "D", // 适合使用图数据库
  graph_db_retrieval: "D", // 图数据库检索(别名)

  // 答案生成
  generate_answer: "n6", // 生成答案结点
  direct_answer: "n7", // 直接回答
};

// RAG选项配置
const ragOptions = [
  { value: "auto", label: "自动判断" },
  { value: "no_retrieval", label: "不开启检索" },
  { value: "vector_only", label: "向量检索" },
  { value: "graph_only", label: "图检索" },
];

// 计算属性
const conversations = computed(() => chatStore.conversations);
const currentConversation = computed(() => chatStore.currentConversation);
const messages = computed(() => chatStore.messages);
const streaming = computed(() => chatStore.streaming);
const loading = computed(() => chatStore.loading);
const citationMetadata = computed(() => chatStore.citationMetadata); // PR-2: 引用元数据
const snippetMap = computed(() => chatStore.snippetMap); // PR-2 阶段D改造: 片段映射

// PR-2 阶段D改造: 证据抽屉状态
const evidenceDrawerVisible = ref(false);
const currentEvidenceDoc = ref(null); // 当前查看的文献信息
const currentEvidenceSnippets = ref([]); // 当前文献的证据片段
const currentEvidenceFullContent = ref(null); // PR-2: 完整chunk内容（用于"查看更多上下文"）
const evidenceExpandedContext = ref(false); // PR-2: 是否展开完整上下文

const findCitationMetadata = (docName) => {
  if (!docName || !citationMetadata.value) {
    return null;
  }

  if (citationMetadata.value[docName]) {
    return citationMetadata.value[docName];
  }

  for (const metadata of Object.values(citationMetadata.value)) {
    if (metadata?.doc_name === docName || metadata?.academic_title === docName) {
      return metadata;
    }
  }

  return null;
};

const toEvidenceSnippet = (snippetId, snippetInfo) => {
  if (!snippetInfo) {
    return [{
      id: snippetId || null,
      badge: snippetId ? snippetId.replace('S', '') : null,
      label: '证据片段',
      text: '',
      context: '',
      cleaned: false,
    }];
  }

  const candidates = Array.isArray(snippetInfo.evidence_candidates) ? snippetInfo.evidence_candidates : [];
  if (snippetId && candidates.length > 0) {
    return candidates.map((candidate, index) => ({
      id: `${snippetId}-${index + 1}`,
      badge: candidates.length > 1 ? `${snippetId.replace('S', '')}-${index + 1}` : snippetId.replace('S', ''),
      label: candidate.label || `证据句 ${index + 1}`,
      text: candidate.text || '',
      context: candidate.context || snippetInfo.excerpt || snippetInfo.content || '',
      cleaned: Boolean(snippetInfo.title_front_matter_cleaned),
    }));
  }

  const text = snippetInfo.highlight || snippetInfo.excerpt || snippetInfo.content || '';
  const context = snippetInfo.excerpt || snippetInfo.content || '';

  return [{
    id: snippetId || null,
    badge: snippetId ? snippetId.replace('S', '') : null,
    label: snippetId ? '证据句' : '证据片段',
    text,
    context,
    cleaned: Boolean(snippetInfo.title_front_matter_cleaned),
  }];
};

const getEvidenceSnippetBadge = (snippet, index) => {
  if (snippet?.badge) {
    return snippet.badge;
  }

  const snippetId = currentEvidenceDoc.value?.snippetId || snippet?.id || '';
  const match = typeof snippetId === 'string' ? snippetId.match(/^S(\d+)(?:-(\d+))?$/) : null;

  if (match) {
    const base = match[1];
    const variant = match[2];

    if (variant) {
      return `${base}-${variant}`;
    }

    if (currentEvidenceDoc.value?.snippetId && currentEvidenceSnippets.value.length > 1) {
      return `${base}-${index + 1}`;
    }

    return base;
  }

  return String(index + 1);
};

// 将消息分组为用户消息和对话轮次（node_updates + assistant）
// 这样可以确保节点更新消息显示在答案上方
const groupedMessages = computed(() => {
  const result = [];
  const msgs = messages.value;
  
  let i = 0;
  while (i < msgs.length) {
    const msg = msgs[i];
    
    if (msg.role === 'user') {
      // 用户消息单独处理
      result.push({
        id: `user-${msg.id}`,
        type: 'user',
        message: msg
      });
      i++;
    } else if (msg.role === 'node_update') {
      // 收集连续的 node_update 消息，直到遇到 assistant 消息
      const nodeUpdates = [];
      while (i < msgs.length && msgs[i].role === 'node_update') {
        nodeUpdates.push(msgs[i]);
        i++;
      }
      
      // 查找后续的 assistant 消息
      let assistant = null;
      if (i < msgs.length && msgs[i].role === 'assistant') {
        assistant = msgs[i];
        i++;
      }
      
      // 创建对话轮次
      result.push({
        id: `turn-${nodeUpdates[0]?.id || Date.now()}`,
        type: 'turn',
        nodeUpdates,
        assistant
      });
    } else if (msg.role === 'assistant') {
      // 单独的 assistant 消息（没有前置的 node_update）
      result.push({
        id: `turn-${msg.id}`,
        type: 'turn',
        nodeUpdates: [],
        assistant: msg
      });
      i++;
    } else {
      // 其他类型消息跳过
      i++;
    }
  }
  
  return result;
});

// 复制内容到剪贴板
const copyToClipboard = async (content) => {
  try {
    await navigator.clipboard.writeText(content);
    ElMessage.success('已复制到剪贴板');
  } catch (err) {
    console.error('复制失败:', err);
    ElMessage.error('复制失败');
  }
};

// 方法
const logout = () => {
  authStore.logout();
  router.push("/login");
};

// 高亮流程图节点 - 带重试机制
const highlightNode = (nodeName, retryCount = 0) => {
  if (!mermaidContainer.value) {
    console.warn("⚠️ mermaidContainer不存在");
    return;
  }

  const nodeId = nodeNameToId[nodeName];
  if (!nodeId) {
    console.warn(`⚠️ 未找到节点映射: ${nodeName}`);
    return;
  }

  console.log(
    "🎯 准备高亮节点:",
    nodeName,
    "-> ID:",
    nodeId,
    retryCount > 0 ? `(重试${retryCount})` : ""
  );

  // 更新当前执行节点显示
  currentExecutingNode.value = getNodeDisplayName(nodeName);

  // 移除所有已有的高亮
  const svg = mermaidContainer.value.querySelector("svg");
  if (!svg) {
    console.warn("⚠️ SVG元素不存在");
    // 如果SVG还未渲染,重试
    if (retryCount < 3) {
      setTimeout(() => {
        highlightNode(nodeName, retryCount + 1);
      }, 300);
    }
    return;
  }

  // 移除所有高亮类
  svg.querySelectorAll(".node-active, .node-completed").forEach((el) => {
    el.classList.remove("node-active", "node-completed");
  });

  // 改进的节点查找逻辑
  let currentNodeGroup = null;

  // 方案1: 通过ID精确匹配 (最常见的情况)
  currentNodeGroup = svg.querySelector(`#flowchart-${nodeId}-0`);

  if (!currentNodeGroup) {
    // 方案2: 查找所有可能的ID格式和选择器
    const possibleSelectors = [
      `#flowchart-${nodeId}`,
      `#${nodeId}`,
      `[id^="flowchart-${nodeId}"]`,
      `g.node[id*="${nodeId}"]`,
      `.node[id*="${nodeId}"]`,
    ];

    for (const selector of possibleSelectors) {
      try {
        currentNodeGroup = svg.querySelector(selector);
        if (currentNodeGroup) {
          console.log("✅ 找到节点，使用选择器:", selector);
          break;
        }
      } catch (e) {
        console.warn("选择器无效:", selector);
      }
    }
  }

  if (!currentNodeGroup) {
    // 方案3: 通过文本内容匹配(备用方案)
    const nodeDisplayName = getNodeDisplayName(nodeName);
    const allNodes = svg.querySelectorAll(
      'g.node, g.node.default, g[class*="node"]'
    );
    for (const node of allNodes) {
      const textContent = node.textContent.trim();
      if (textContent === nodeDisplayName) {
        currentNodeGroup = node;
        console.log("✅ 通过文本内容找到节点:", nodeDisplayName);
        break;
      }
    }
  }

  if (currentNodeGroup) {
    currentNodeGroup.classList.add("node-active");
    console.log("✅ 已添加node-active类到节点:", nodeName);

    // 3秒后将当前节点标记为已完成
    setTimeout(() => {
      if (currentNodeGroup) {
        currentNodeGroup.classList.remove("node-active");
        currentNodeGroup.classList.add("node-completed");
        console.log("✅ 节点标记为已完成:", nodeName);
      }
    }, 3000);
  } else {
    console.warn("⚠️ 未找到节点元素，nodeId:", nodeId, "nodeName:", nodeName);

    // 重试机制 - 如果是前几次重试,可能是Mermaid还未完全渲染
    if (retryCount < 3) {
      console.log(`🔄 将在300ms后重试...`);
      setTimeout(() => {
        highlightNode(nodeName, retryCount + 1);
      }, 300);
    } else {
      // 最后一次重试失败,打印调试信息
      console.log("📋 SVG中所有的节点元素:");
      const allNodes = Array.from(
        svg.querySelectorAll('g.node, g[class*="node"]')
      );
      allNodes.forEach((node, index) => {
        console.log(`节点${index}:`, {
          id: node.id,
          class: node.className.baseVal || node.className,
          text: node.textContent.trim().substring(0, 30),
        });
      });
    }
  }
};

// 清除所有节点高亮
const clearNodeHighlights = () => {
  currentExecutingNode.value = "";
  if (!mermaidContainer.value) return;

  const svg = mermaidContainer.value.querySelector("svg");
  if (svg) {
    svg.querySelectorAll(".node-active, .node-completed").forEach((el) => {
      el.classList.remove("node-active", "node-completed");
    });
  }
};

const createNewConversation = async () => {
  chatStore.createLocalConversation();
};

const selectConversation = async (conversationId) => {
  // 如果点击的是当前对话，不做任何操作
  if (currentConversation.value?.id === conversationId) {
    return;
  }

  // 保存待切换的对话ID
  pendingConversationId.value = conversationId;

  // 标记这是为了切换对话而打开的设置
  isSettingsForConversationSwitch.value = true;

  // 打开设置对话框
  settingsModalOpen.value = true;
};

const deleteConversation = async (conversationId) => {
  try {
    await ElMessageBox.confirm("确定要删除这个对话吗？", "删除确认", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    try {
      await chatStore.deleteConversation(conversationId);
      // 删除成功，可以添加成功提示
      console.log("对话删除成功");
    } catch (error) {
      console.error("删除对话失败:", error);
      // 可以在这里添加错误提示
      ElMessageBox.alert("删除对话失败，请稍后重试", "错误", {
        confirmButtonText: "确定",
        type: "error",
      });
    }
  } catch {
    // 用户取消删除
  }
};

const sendMessage = async () => {
  if (!newMessage.value.trim() || streaming.value) return;

  const message = newMessage.value.trim();
  newMessage.value = "";
  resetTextareaHeight(); // 重置输入框高度

  try {
    console.log("📤 准备发送消息");
    console.log("  当前选中的知识库ID:", selectedLibrary.value);
    console.log("  RAG模式:", ragMode.value);

    const messageData = {
      content: message,
      ragMode: ragMode.value,
      maxRetrievalDocs: maxRetrievalDocs.value,
      systemPrompt: systemPrompt.value,
    };

    // 只有在选中知识库时才添加collection_id
    if (selectedLibrary.value) {
      const collectionId = getSelectedLibraryCollectionId(
        selectedLibrary.value
      );
      console.log("  知识库collection_id:", collectionId);
      if (collectionId) {
        messageData.collection_id = collectionId;
      }
    } else {
      console.log("  未选择知识库，不添加collection_id");
    }
    console.log("📤 发送消息数据:", messageData);

    await chatStore.sendMessage(messageData);
    scrollToBottom();
  } catch (error) {
    console.error("发送消息失败:", error);
    // 可以在这里添加错误提示
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

const resolveCitationTarget = (event) => {
  const block = event?.currentTarget?.closest('p, li');
  if (!block) {
    return null;
  }

  const blockText = block.textContent?.trim() || '';
  if (!blockText) {
    return null;
  }

  if (/^(引用片段索引|参考文献)/.test(blockText)) {
    return null;
  }

  if (/^\[S?\d+\]\s/.test(blockText)) {
    return null;
  }

  return block;
};

const setCitationTargetHover = (event, isActive) => {
  const target = resolveCitationTarget(event);
  if (!target) {
    return;
  }

  target.classList.toggle('citation-target-hover', isActive);
};

const activateCitationScope = (event) => {
  const target = resolveCitationTarget(event);
  if (!target) {
    return;
  }

  target.classList.remove('citation-target-active');
  void target.offsetWidth;
  target.classList.add('citation-target-active');

  window.setTimeout(() => {
    target.classList.remove('citation-target-active');
  }, 1800);
};

// 渲染markdown内容
const renderMarkdown = (content) => {
  // 预处理：修复 LaTeX 公式格式
  // markdown-it-texmath 不支持 `$ P $` 这种带空格的格式，需要转换为 `$P$`
  let processedContent = content;

  // 处理行内公式：`$ ... $` -> `$...$`（移除美元符号内侧的空格）
  // 匹配 $ 后有空格，或 $ 前有空格的情况
  processedContent = processedContent.replace(
    /\$\s+([^$]+?)\s+\$/g,
    (match, inner) => `$${inner.trim()}$`
  );

  // 处理只有一侧有空格的情况
  processedContent = processedContent.replace(
    /\$\s+([^$]+?)\$/g,
    (match, inner) => `$${inner.trim()}$`
  );
  processedContent = processedContent.replace(
    /\$([^$]+?)\s+\$/g,
    (match, inner) => `$${inner.trim()}$`
  );

  // 转义特殊标记：防止类似 <image> <pcd> <obj> <loc0-255> 等被当作 HTML 标签
  // 这些标记常见于机器人、3D视觉等领域的论文中
  // 匹配模式：<标识符> 或 </标识符> 或 <标识符数字> 等，但排除常见 HTML 标签
  const htmlTags = ['p', 'div', 'span', 'a', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 
                    'img', 'code', 'pre', 'blockquote', 'em', 'strong', 'b', 'i', 'u',
                    'sup', 'sub', 'del', 's', 'mark', 'small', 'big', 'svg', 'path'];
  
  processedContent = processedContent.replace(
    /<\/?([a-zA-Z][a-zA-Z0-9_\-\/]*?)>/g,
    (match, tagName) => {
      // 如果是常见 HTML 标签，保持原样
      const lowerTag = tagName.toLowerCase().replace('/', '');
      if (htmlTags.includes(lowerTag)) {
        return match;
      }
      // 否则转义尖括号，使其显示为文本
      return match.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
  );

  // PR-2 阶段D改造: 解析参考文献部分，建立片段编号到文献名的映射
  // 匹配格式如: [S1] 文献名称 或 [1] 文献名称（向后兼容）
  const textCitationMap = {};
  const refPatternS = /\[S(\d+)\]\s*([^\n\[]+)/g;
  let refMatch;
  while ((refMatch = refPatternS.exec(content)) !== null) {
    const num = refMatch[1];
    const name = refMatch[2].trim();
    if (name.length > 2 && name.length < 200) {
      textCitationMap[`S${num}`] = name;
    }
  }
  // 兼容旧格式 [1] 文献名称
  const refPatternOld = /\[(\d+)\]\s*([^\n\[]+)/g;
  while ((refMatch = refPatternOld.exec(content)) !== null) {
    const num = refMatch[1];
    const name = refMatch[2].trim();
    if (name.length > 5 && name.length < 200) {
      textCitationMap[num] = name;
    }
  }

  // 渲染 Markdown
  let html = md.render(processedContent);

  // PR-2 阶段D改造: 后处理 - 为引用标记 [S1] [S2] 添加增强样式和tooltip
  // 同时兼容旧格式 [1] [2]
  // 先处理 [S数字] 格式（新格式）
  html = html.replace(
    /\[S(\d+)\]/g,
    (match, num) => {
      const snippetId = `S${num}`;
      // 从 snippetMap 获取片段信息
      const snippetInfo = snippetMap.value ? snippetMap.value[snippetId] : null;
      // 从 textCitationMap 获取文献名
      const docName = textCitationMap[snippetId] || (snippetInfo ? snippetInfo.source : '');

      // 构建 tooltip
      let tooltipContent = `片段 ${snippetId}`;
      let hasMetadata = false;

      if (snippetInfo) {
        const parts = [];
        // 片段来源
        parts.push(`来源: ${snippetInfo.source}`);
        // 片段内容预览（前100字）
        if (snippetInfo.content) {
          const previewSource = snippetInfo.excerpt || snippetInfo.highlight || snippetInfo.content;
          const preview = previewSource.substring(0, 100) + (previewSource.length > 100 ? '...' : '');
          parts.push(`内容: ${preview}`);
        }
        tooltipContent = parts.join('\n');
      }

      // 尝试从 citationMetadata 查找文献学术信息
      if (docName && citationMetadata.value) {
        const metadata = findCitationMetadata(docName);
        if (metadata) {
          hasMetadata = true;
          const parts = [];
          if (metadata.academic_title) parts.push(`📄 ${metadata.academic_title}`);
          else parts.push(`📄 ${docName}`);
          if (metadata.authors && metadata.authors.length > 0) {
            const authorStr = metadata.authors.length > 3
              ? `${metadata.authors.slice(0, 3).join(', ')} 等`
              : metadata.authors.join(', ');
            parts.push(`👤 ${authorStr}`);
          }
          if (metadata.publish_year) parts.push(`📅 ${metadata.publish_year}年`);
          if (snippetInfo && (snippetInfo.excerpt || snippetInfo.highlight || snippetInfo.content)) {
            const previewSource = snippetInfo.excerpt || snippetInfo.highlight || snippetInfo.content;
            const preview = previewSource.substring(0, 80) + (previewSource.length > 80 ? '...' : '');
            parts.push(`📝 ${preview}`);
          }
          tooltipContent = parts.join('\n');
        }
      }

      const escapedTooltip = tooltipContent.replace(/"/g, '&quot;').replace(/\n/g, '&#10;');
      const badgeClass = hasMetadata ? 'citation-badge citation-badge-enhanced' : 'citation-badge';

      // 点击时传递片段编号
      return `<span class="${badgeClass} citation-clickable" title="${escapedTooltip}" data-snippet-id="${snippetId}" onmouseenter="window.setCitationTargetHover && window.setCitationTargetHover(event, true)" onmouseleave="window.setCitationTargetHover && window.setCitationTargetHover(event, false)" onclick="window.activateCitationScope && window.activateCitationScope(event); window.openEvidenceDrawer && window.openEvidenceDrawer('${snippetId}')">[${snippetId}]</span>`;
    }
  );

  // 兼容旧格式 [数字]（如果 LLM 没有使用新格式）
  html = html.replace(
    /\[(\d+)\]/g,
    (match, num) => {
      const docName = textCitationMap[num];

      let tooltipContent = `引用 ${num}`;
      let hasMetadata = false;

      if (docName && citationMetadata.value) {
        const metadata = findCitationMetadata(docName);
        if (metadata) {
          hasMetadata = true;
          const parts = [];
          if (metadata.academic_title) parts.push(`📄 ${metadata.academic_title}`);
          else parts.push(`📄 ${docName}`);
          if (metadata.authors && metadata.authors.length > 0) {
            const authorStr = metadata.authors.length > 3
              ? `${metadata.authors.slice(0, 3).join(', ')} 等`
              : metadata.authors.join(', ');
            parts.push(`👤 ${authorStr}`);
          }
          if (metadata.publish_year) parts.push(`📅 ${metadata.publish_year}年`);
          if (metadata.doi) parts.push(`🔗 DOI: ${metadata.doi}`);
          tooltipContent = parts.join('\n');
        }
      }

      if (!hasMetadata && docName) {
        tooltipContent = docName;
      }

      const escapedTooltip = tooltipContent.replace(/"/g, '&quot;').replace(/\n/g, '&#10;');
      const escapedDocName = docName ? docName.replace(/"/g, '&quot;') : '';
      const badgeClass = hasMetadata ? 'citation-badge citation-badge-enhanced' : 'citation-badge';

      return `<span class="${badgeClass} citation-clickable" title="${escapedTooltip}" data-citation="${num}" data-doc-name="${escapedDocName}" onmouseenter="window.setCitationTargetHover && window.setCitationTargetHover(event, true)" onmouseleave="window.setCitationTargetHover && window.setCitationTargetHover(event, false)" onclick="window.activateCitationScope && window.activateCitationScope(event); window.openEvidenceDrawer && window.openEvidenceDrawer('${escapedDocName}')">[${num}]</span>`;
    }
  );

  return html;
};

// 获取节点显示名称
const getNodeDisplayName = (nodeName) => {
  const nodeNameMap = {
    start: "开始",
    check_retrieval_needed: "检索需求判断",
    expand_subquestions: "子问题扩展",
    classify_question_type: "问题类型分类",
    vector_db_retrieval: "向量数据库检索",
    graph_db_retrieval: "图数据库检索",
    graph_db_retrieval_node: "图数据库检索",
    generate_answer: "生成答案",
    direct_answer: "直接回答",
    answer_generation: "答案生成",
    end: "结束",
  };
  return nodeNameMap[nodeName] || nodeName;
};

// PR-2 阶段D改造: 打开证据抽屉，支持按片段编号精确查找
const openEvidenceDrawer = (idOrDocName) => {
  if (!idOrDocName) {
    ElMessage.info('暂无原文信息');
    return;
  }

  // 判断是片段编号(S1, S2...)还是文献名
  const isSnippetId = /^S\d+$/.test(idOrDocName);

  if (isSnippetId && snippetMap.value && snippetMap.value[idOrDocName]) {
    // 新格式：精确查找单个片段
    const snippetInfo = snippetMap.value[idOrDocName];
    const docName = snippetInfo.source || '未知来源';

    // 查找文献元数据
    let metadata = null;
    if (citationMetadata.value) {
      metadata = findCitationMetadata(docName);
    }

    // 设置当前查看的文献信息
    currentEvidenceDoc.value = {
      name: docName,
      title: metadata?.academic_title || docName,
      authors: metadata?.authors || [],
      year: metadata?.publish_year,
      doi: metadata?.doi,
      sourceType: metadata?.source_type,
      snippetId: idOrDocName  // 当前片段编号
    };
    currentEvidenceSnippets.value = toEvidenceSnippet(idOrDocName, snippetInfo);
    currentEvidenceFullContent.value = snippetInfo.content;  // 完整内容供展开查看
    evidenceExpandedContext.value = false;  // 重置展开状态
    evidenceDrawerVisible.value = true;
  } else {
    // 旧格式兼容：按文献名查找
    let metadata = null;
    if (citationMetadata.value) {
      metadata = findCitationMetadata(idOrDocName);
    }

    // 从 snippetMap 中收集该文献的所有片段
    let snippets = [];
    if (snippetMap.value) {
      for (const [sid, info] of Object.entries(snippetMap.value)) {
        if (info.source === idOrDocName || info.raw_source === idOrDocName) {
          snippets.push(...toEvidenceSnippet(sid, info).slice(0, 1));
        }
      }

      snippets.sort((left, right) => {
        const leftMatch = typeof left?.id === 'string' ? left.id.match(/^S(\d+)/) : null;
        const rightMatch = typeof right?.id === 'string' ? right.id.match(/^S(\d+)/) : null;
        return Number(leftMatch?.[1] || 0) - Number(rightMatch?.[1] || 0);
      });
    }

    if (snippets.length === 0 && !metadata) {
      ElMessage.info('暂无该文献的证据片段');
      return;
    }

    currentEvidenceDoc.value = {
      name: idOrDocName,
      title: metadata?.academic_title || idOrDocName,
      authors: metadata?.authors || [],
      year: metadata?.publish_year,
      doi: metadata?.doi,
      sourceType: metadata?.source_type
    };
    currentEvidenceSnippets.value = snippets;
    currentEvidenceFullContent.value = null;  // 多片段模式不需要展开
    evidenceExpandedContext.value = false;
    evidenceDrawerVisible.value = true;
  }
};

// 将函数暴露到 window 对象，供 v-html 中的 onclick 调用
onMounted(async () => {
  window.openEvidenceDrawer = openEvidenceDrawer;
  window.activateCitationScope = activateCitationScope;
  window.setCitationTargetHover = setCitationTargetHover;
});

// 加载知识库列表
const loadKnowledgeLibraries = async () => {
  try {
    librariesLoading.value = true;
    const response = await knowledgeAPI.getLibraries();

    if (response.status === 200) {
      knowledgeLibraries.value = response.data || [];
    } else {
      console.error("获取知识库列表失败:", response.msg);
      knowledgeLibraries.value = [];
    }
  } catch (error) {
    console.error("加载知识库列表失败:", error);
    knowledgeLibraries.value = [];
  } finally {
    librariesLoading.value = false;
  }
};

// 获取RAG模式文本（单选）
const getRagModeText = (mode) => {
  const option = ragOptions.find((opt) => opt.value === mode);
  return option ? option.label : mode;
};

// 获取选中知识库名称
const getSelectedLibraryName = (libraryId) => {
  const library = knowledgeLibraries.value.find((lib) => lib.id === libraryId);
  return library ? library.title : "未知知识库";
};

// 获取选中知识库的collection_id
const getSelectedLibraryCollectionId = (libraryId) => {
  const library = knowledgeLibraries.value.find((lib) => lib.id === libraryId);
  return library ? library.collection_id : null;
};

// 加载选中知识库的文献列表
const loadSelectedLibraryDocuments = async (libraryId) => {
  if (!libraryId) {
    selectedLibraryDocuments.value = [];
    return;
  }
  
  try {
    const response = await knowledgeAPI.getLibraryDetail(libraryId);
    if (response.status === 200 && response.data) {
      selectedLibraryDocuments.value = response.data.documents || [];
      console.log(`📚 已加载知识库文献列表: ${selectedLibraryDocuments.value.length} 个文献`);
    } else {
      selectedLibraryDocuments.value = [];
    }
  } catch (error) {
      console.error("加载知识库文献列表失败:", error);
    selectedLibraryDocuments.value = [];
  }
};

// PR-2: 加载知识库的学术引用元数据（用于历史对话显示）
const loadCitationMetadata = async (libraryId) => {
  if (!libraryId) {
    chatStore.citationMetadata = {};
    return;
  }

  try {
    // 获取知识库的 collection_id
    const collectionId = getSelectedLibraryCollectionId(libraryId);
    if (!collectionId) {
      console.log('📚 未找到 collection_id，跳过加载引用元数据');
      return;
    }

    const response = await knowledgeAPI.getCitationMetadata(collectionId);
    if (response.status === 200 && response.data) {
      chatStore.citationMetadata = response.data;
      console.log(`📚 已加载引用元数据: ${Object.keys(response.data).length} 个文献`);
    }
  } catch (error) {
    console.error("加载引用元数据失败:", error);
    // 失败时不影响正常使用
  }
};

// 点击标签插入文献名称到输入框（支持撤销）
const insertDocumentName = (name) => {
  const textarea = messageInputRef.value;
  if (!textarea) {
    // 降级方案：如果无法获取 textarea 引用，直接修改
    if (newMessage.value) {
      newMessage.value = newMessage.value.trimEnd() + ' ' + name + ' ';
    } else {
      newMessage.value = name + ' ';
    }
    return;
  }

  // 聚焦到输入框
  textarea.focus();
  
  // 准备插入的文本
  const textToInsert = newMessage.value ? ' ' + name + ' ' : name + ' ';
  
  // 将光标移到末尾
  const len = textarea.value.length;
  textarea.setSelectionRange(len, len);
  
  // 使用 execCommand 插入文本（支持浏览器原生撤销）
  // 注意：execCommand 虽然已被标记为废弃，但在大多数浏览器中仍然有效
  // 且这是目前唯一能支持原生撤销的方法
  const success = document.execCommand('insertText', false, textToInsert);
  
  if (!success) {
    // 某些浏览器可能不支持 execCommand('insertText')
    // 降级方案：使用 InputEvent
    try {
      const inputEvent = new InputEvent('input', {
        bubbles: true,
        cancelable: true,
        inputType: 'insertText',
        data: textToInsert
      });
      // 手动更新值并触发事件
      textarea.value = textarea.value.substring(0, len) + textToInsert;
      newMessage.value = textarea.value;
      textarea.dispatchEvent(inputEvent);
    } catch (e) {
      // 最终降级：直接修改
      newMessage.value = newMessage.value.trimEnd() + textToInsert;
    }
  } else {
    // execCommand 成功后，同步 v-model 值
    newMessage.value = textarea.value;
  }
  
  // 调整高度
  nextTick(() => {
    adjustTextareaHeight({ target: textarea });
  });
};

// 调整 textarea 高度以适应内容
const adjustTextareaHeight = (event) => {
  const textarea = event.target;
  if (!textarea) return;
  
  // 重置高度以获取正确的 scrollHeight
  textarea.style.height = 'auto';
  // 设置新高度，限制最大高度
  const newHeight = Math.min(textarea.scrollHeight, 200);
  textarea.style.height = newHeight + 'px';
  
  // 如果内容超过最大高度，显示滚动条
  if (textarea.scrollHeight > 200) {
    textarea.style.overflowY = 'auto';
  } else {
    textarea.style.overflowY = 'hidden';
  }
};

// 重置 textarea 高度（发送消息后调用）
const resetTextareaHeight = () => {
  const textarea = messageInputRef.value;
  if (textarea) {
    textarea.style.height = '42px';
    textarea.style.overflowY = 'hidden';
  }
};

// 处理键盘事件：Enter 发送，Shift+Enter 换行
const handleKeydown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
};

// 截断过长的文献名称
const truncateText = (text, maxLength) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// 监听知识库选择变化，加载文献列表
watch(selectedLibrary, (newLibraryId) => {
  loadSelectedLibraryDocuments(newLibraryId);
  // PR-2: 选择知识库时获取学术元数据，用于历史对话显示
  loadCitationMetadata(newLibraryId);
});

// 监听点击外部关闭下拉框
onMounted(async () => {
  // 初始化Mermaid
  mermaid.initialize({
    startOnLoad: false, // 改为false,手动控制渲染时机
    theme: "default",
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: "basis",
      padding: 20, // 增加内边距,避免边缘裁剪
    },
    // 禁用安全级别以允许更好的渲染
    securityLevel: "loose",
  });

  // 等待DOM渲染完成后手动渲染Mermaid图表
  await nextTick();
  if (mermaidContainer.value) {
    try {
      await mermaid.run({
        querySelector: ".mermaid",
      });
      console.log("✅ Mermaid图表渲染完成");
    } catch (error) {
      console.error("❌ Mermaid渲染失败:", error);
    }
  }

  // 恢复Agent面板宽度
  restorePanelWidth();
  restoreEvidenceDrawerWidth();

  // 加载聊天历史
  if (authStore.isAuthenticated) {
    try {
      await chatStore.loadChatHistory();
      // 加载知识库列表
      await loadKnowledgeLibraries();

      // 从本地存储加载RAG模式设置
      const savedRagMode = localStorage.getItem("ragMode");
      if (savedRagMode) {
        ragMode.value = savedRagMode;
      }

      // 从本地存储加载选中的知识库
      const savedLibrary = localStorage.getItem("selectedLibrary");
      if (savedLibrary) {
        selectedLibrary.value = savedLibrary;
      }

      // 检查是否需要显示知识库选择弹窗
      // 延迟一下，让页面先渲染完成
      setTimeout(() => {
        checkShowLibrarySelectDialog();
      }, 500);
    } catch (error) {
      console.error("加载聊天历史失败:", error);
    }
  } else {
    router.push("/login");
  }
});

// 监听消息变化，自动滚动到底部
watch(
  messages,
  (newMessages, oldMessages) => {
    console.log("🔄 Messages数组发生变化:");
    console.log("  新消息数量:", newMessages.length);
    console.log("  旧消息数量:", oldMessages ? oldMessages.length : 0);
    console.log("  最新消息:", newMessages[newMessages.length - 1]);

    // 检查最后一条消息
    const lastMessage = newMessages[newMessages.length - 1];

    // 如果是节点更新消息,高亮对应节点
    if (lastMessage && lastMessage.role === "node_update") {
      console.log("🎯 检测到节点更新:", lastMessage.node_name);
      // 使用nextTick确保DOM已更新,再用延迟确保Mermaid已渲染
      // 增加延迟时间以确保Mermaid完全渲染完成
      nextTick(() => {
        setTimeout(() => {
          highlightNode(lastMessage.node_name);
        }, 200); // 从100ms增加到200ms
      });
    }

    // 如果是用户消息,清除之前的高亮
    if (lastMessage && lastMessage.role === "user") {
      clearNodeHighlights();
    }

    // 检查最后一条AI消息的内容变化
    const lastAiMessage = newMessages
      .filter((m) => m.role === "assistant")
      .pop();
    if (lastAiMessage) {
      console.log("  最后一条AI消息内容长度:", lastAiMessage.content.length);
      console.log(
        "  最后一条AI消息内容预览:",
        lastAiMessage.content.substring(0, 50) + "..."
      );
    }

    scrollToBottom();
  },
  { deep: true }
);

// 添加一个专门监听消息内容变化的watcher
watch(
  () => messages.value.map((m) => m.content),
  (newContents, oldContents) => {
    console.log("📝 消息内容发生变化:");
    newContents.forEach((content, index) => {
      const oldContent = oldContents ? oldContents[index] : "";
      if (content !== oldContent) {
        console.log(`  消息${index}内容变化:`, {
          old: oldContent ? oldContent.substring(0, 30) + "..." : "空",
          new: content.substring(0, 30) + "...",
          length: content.length,
        });
      }
    });
  },
  { deep: true }
);

// 监听RAG模式变化并保存到本地存储
watch(ragMode, (newMode) => {
  console.log("🔄 RAG模式变化:", newMode);
  localStorage.setItem("ragMode", newMode);
});

// 监听知识库选择变化并保存到本地存储
watch(selectedLibrary, (newLibrary) => {
  console.log("🔄 知识库选择变化:", newLibrary);
  const libraryName = newLibrary
    ? getSelectedLibraryName(newLibrary)
    : "不使用知识库";
  console.log("  -> 知识库名称:", libraryName);
  localStorage.setItem("selectedLibrary", newLibrary);
});

onUnmounted(() => {
  document.removeEventListener("mousemove", handleResize);
  document.removeEventListener("mouseup", stopResize);
  document.removeEventListener("mousemove", handleEvidenceResize);
  document.removeEventListener("mouseup", stopEvidenceResize);
  delete window.openEvidenceDrawer;
  delete window.activateCitationScope;
  delete window.setCitationTargetHover;
});

// 检查认证状态
if (!authStore.isAuthenticated) {
  router.push("/login");
}

// 获取RAG模式描述
const getRagModeDescription = (mode) => {
  const descriptions = {
    auto: "系统自动判断是否需要检索知识库",
    no_retrieval: "直接使用AI模型回答，不检索知识库",
    vector_only: "仅使用向量检索获取相关文档",
    graph_only: "仅使用图检索获取相关文档",
  };
  return descriptions[mode] || "未知模式";
};

// 打开设置弹窗
const openSettingsModal = () => {
  isSettingsForConversationSwitch.value = false;
  settingsModalOpen.value = true;
};

// 关闭设置弹窗（确认保存）
const closeSettingsModal = async () => {
  settingsModalOpen.value = false;
  ElMessage.success("设置已保存");

  // 如果是为了切换对话而打开的设置，现在执行切换
  if (isSettingsForConversationSwitch.value && pendingConversationId.value) {
    await chatStore.selectConversation(pendingConversationId.value);

    // 重置标记
    isSettingsForConversationSwitch.value = false;
    pendingConversationId.value = null;
  }
};

// 取消设置弹窗（不保存）
const cancelSettingsModal = () => {
  settingsModalOpen.value = false;

  // 重置标记，不执行对话切换
  if (isSettingsForConversationSwitch.value) {
    isSettingsForConversationSwitch.value = false;
    pendingConversationId.value = null;
  }
};

// 重置设置
const resetSettings = () => {
  ragMode.value = "auto";
  selectedLibrary.value = "";
  maxRetrievalDocs.value = 5;
  systemPrompt.value =
    "你是一个专业的RAG助手，能够基于检索到的信息提供准确的回答。";
};

// 确认知识库选择
const confirmLibrarySelection = () => {
  selectedLibrary.value = selectedLibraryForDialog.value;

  // 保存到localStorage
  localStorage.setItem("selectedLibrary", selectedLibrary.value);

  // 如果选择了"不再显示"，保存到localStorage
  if (dontShowLibrarySelectAgain.value) {
    localStorage.setItem("dontShowLibrarySelect", "true");
  }

  showLibrarySelectDialog.value = false;
};

// 跳过知识库选择
const skipLibrarySelection = () => {
  // 如果选择了"不再显示"，保存到localStorage
  if (dontShowLibrarySelectAgain.value) {
    localStorage.setItem("dontShowLibrarySelect", "true");
  }

  showLibrarySelectDialog.value = false;
};

// 跳转到文档库管理页面
const goToDocumentLibrary = () => {
  showLibrarySelectDialog.value = false;
  router.push("/document-library");
};

// 检查是否需要显示知识库选择弹窗
const checkShowLibrarySelectDialog = () => {
  const dontShow = localStorage.getItem("dontShowLibrarySelect");
  const savedLibrary = localStorage.getItem("selectedLibrary");

  // 如果用户选择了"不再显示"或已经选择过知识库，则不显示弹窗
  if (dontShow === "true" || savedLibrary) {
    return;
  }

  // 显示知识库选择弹窗
  showLibrarySelectDialog.value = true;
  selectedLibraryForDialog.value = selectedLibrary.value;
};

// Agent面板调整大小相关函数
const startResize = (e) => {
  isResizing.value = true;
  startX.value = e.clientX;
  startWidth.value = agentPanelWidth.value;

  // 添加鼠标移动和释放事件监听
  document.addEventListener("mousemove", handleResize);
  document.addEventListener("mouseup", stopResize);

  // 防止文本选择
  e.preventDefault();
};

const handleResize = (e) => {
  if (!isResizing.value) return;

  // 计算新宽度 (向左拖动增加宽度,向右拖动减少宽度)
  const deltaX = startX.value - e.clientX;
  const newWidth = startWidth.value + deltaX;

  // 限制最小和最大宽度
  const minWidth = 300; // 最小300px
  const maxWidth = 800; // 最大800px

  if (newWidth >= minWidth && newWidth <= maxWidth) {
    agentPanelWidth.value = newWidth;
  }
};

const stopResize = () => {
  isResizing.value = false;

  // 移除事件监听
  document.removeEventListener("mousemove", handleResize);
  document.removeEventListener("mouseup", stopResize);

  // 保存宽度到localStorage
  localStorage.setItem("agentPanelWidth", agentPanelWidth.value.toString());
};

const startEvidenceResize = (e) => {
  isEvidenceResizing.value = true;
  evidenceStartX.value = e.clientX;
  evidenceStartWidth.value = evidenceDrawerWidth.value;

  document.addEventListener("mousemove", handleEvidenceResize);
  document.addEventListener("mouseup", stopEvidenceResize);

  e.preventDefault();
};

const handleEvidenceResize = (e) => {
  if (!isEvidenceResizing.value) return;

  const deltaX = evidenceStartX.value - e.clientX;
  const newWidth = evidenceStartWidth.value + deltaX;

  const minWidth = 420;
  const maxWidth = Math.min(window.innerWidth - 120, 1100);

  if (newWidth >= minWidth && newWidth <= maxWidth) {
    evidenceDrawerWidth.value = newWidth;
  }
};

const stopEvidenceResize = () => {
  isEvidenceResizing.value = false;

  document.removeEventListener("mousemove", handleEvidenceResize);
  document.removeEventListener("mouseup", stopEvidenceResize);

  localStorage.setItem("evidenceDrawerWidth", evidenceDrawerWidth.value.toString());
};

// 从localStorage恢复面板宽度
const restorePanelWidth = () => {
  const savedWidth = localStorage.getItem("agentPanelWidth");
  if (savedWidth) {
    const width = parseInt(savedWidth);
    if (width >= 300 && width <= 800) {
      agentPanelWidth.value = width;
    }
  }
};

const restoreEvidenceDrawerWidth = () => {
  const savedWidth = localStorage.getItem("evidenceDrawerWidth");
  if (savedWidth) {
    const width = parseInt(savedWidth);
    const maxWidth = Math.min(window.innerWidth - 120, 1100);
    if (width >= 420 && width <= maxWidth) {
      evidenceDrawerWidth.value = width;
    }
  }
};
</script>

<style scoped>
/* 滑块样式 */
.slider::-webkit-slider-thumb {
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* 节点更新样式 */
.node-update-details {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin: 8px 0;
  background: #f9fafb;
}

.node-update-summary {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
  background: #f3f4f6;
  border-radius: 8px 8px 0 0;
}

.node-update-details[open] .node-update-summary {
  border-bottom: 1px solid #e5e7eb;
  border-radius: 8px 8px 0 0;
}

.node-update-caret {
  transition: transform 0.2s ease;
}

.node-update-details[open] .node-update-caret {
  transform: rotate(90deg);
}

.node-update-title {
  flex: 1;
}

.node-update-content {
  padding: 16px;
}

.node-update-content-text {
  color: #374151;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* 引用标记样式 - 使用 :deep() 穿透 v-html 动态内容 */
:deep(.citation-badge) {
  display: inline-block;
  color: #2563eb;
  font-size: 0.85em;
  font-weight: 600;
  background: #eff6ff;
  padding: 1px 5px;
  border-radius: 4px;
  margin: 0 1px;
  cursor: default;
  transition: all 0.15s ease;
}

:deep(.citation-badge:hover) {
  background: #dbeafe;
  color: #1d4ed8;
}

/* PR-2: 增强引用标记样式 - 有完整学术元数据时显示金色样式 */
:deep(.citation-badge-enhanced) {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

:deep(.citation-badge-enhanced:hover) {
  background: #fde68a;
  color: #78350f;
}

/* PR-2 阶段D: 可点击的引用标记样式 */
:deep(.citation-clickable) {
  cursor: pointer;
  transition: all 0.2s ease;
}

:deep(.citation-clickable:hover) {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

:deep(.citation-clickable:active) {
  transform: scale(0.95);
}

:deep(.prose p.citation-target-hover),
:deep(.prose li.citation-target-hover) {
  background: rgba(251, 191, 36, 0.1);
  box-shadow: inset 3px 0 0 rgba(245, 158, 11, 0.35);
  border-radius: 8px;
  transition: background-color 0.18s ease, box-shadow 0.18s ease;
}

:deep(.prose p.citation-target-active),
:deep(.prose li.citation-target-active) {
  background: rgba(251, 191, 36, 0.16);
  box-shadow: inset 3px 0 0 rgba(217, 119, 6, 0.5);
  border-radius: 8px;
}
</style>