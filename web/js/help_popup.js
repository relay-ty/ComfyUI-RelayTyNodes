/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - 帮助弹窗前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   为所有 RelayTyNodes 分类下的节点提供 Markdown 格式的帮助弹窗功能。
 *
 * 关联节点:
 *   - 全局生效：对所有 category 以 "RelayTyNodes" 开头的节点启用帮助弹窗
 *   - 无特定关联后端节点，属于通用前端工具类扩展
 *
 * 扩展功能:
 *   - 读取节点 DESCRIPTION 属性中的 Markdown 内容，渲染为 HTML 弹窗
 *   - 支持 marked + DOMPurify（如果可用）渲染安全 HTML，否则使用内置简单渲染器
 *   - 可通过 ComfyUI 设置界面中的 "RelayTyNodes.helpPopup" 开关启用/禁用
 *
 * =============================================================================
 */

const { app } = window.comfyAPI.app;

// 加载依赖脚本
const loadScript = (FILE_URL, async = true, type = 'text/javascript') => {
  return new Promise((resolve, reject) => {
    try {
      const existingScript = document.querySelector(`script[src="${FILE_URL}"]`);
      if (existingScript) {
        resolve({ status: true, message: 'Script already loaded' });
        return;
      }
      const scriptEle = document.createElement('script');
      scriptEle.type = type;
      scriptEle.async = async;
      scriptEle.src = FILE_URL;
      scriptEle.addEventListener('load', (ev) => resolve({ status: true }));
      scriptEle.addEventListener('error', (ev) => 
        reject({ status: false, message: `Failed to load ${FILE_URL}` })
      );
      document.body.appendChild(scriptEle);
    } catch (error) {
      reject(error);
    }
  });
};

// 尝试加载第三方库（如果可用）
loadScript('kjweb_async/marked.min.js').catch(() => {});
loadScript('kjweb_async/purify.min.js').catch(() => {});

// 我们节点的分类
const categories = ["RelayTyNodes"];
const nodeDescriptions = new Map();

function isHelpPopupEnabled() {
  return app.ui.settings.getSettingValue("RelayTyNodes.helpPopup") !== false;
}

app.registerExtension({
  name: "RelayTyNodes.HelpPopup",
  
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!isHelpPopupEnabled()) return;
    try {
      categories.forEach(category => {
        if (nodeData?.category?.startsWith(category)) {
          if (nodeData.description) {
            nodeDescriptions.set(nodeData.name, nodeData.description);
          }
          addDocumentation(nodeData, nodeType);
        }
      });
    } catch (error) {
      console.error("Error in registering RelayTyNodes.HelpPopup", error);
    }
  },
  
  nodeCreated(node) {
    if (!isHelpPopupEnabled()) return;
    const description = nodeDescriptions.get(node.type) || nodeDescriptions.get(node.comfyClass);
    if (description) {
      node._rtHelpDescription = description;
    }
  },
  
  setup() {
    if (!isHelpPopupEnabled()) return;
    setupHelpObserver();
  },
});

// 创建样式表 - 修复滚动条问题
const create_documentation_stylesheet = () => {
  const tag = 'rt-documentation-stylesheet';
  let styleTag = document.getElementById(tag);
  
  if (!styleTag) {
    styleTag = document.createElement('style');
    styleTag.type = 'text/css';
    styleTag.id = tag;
    styleTag.innerHTML = `
      .rt-documentation-popup {
        background: var(--comfy-menu-bg);
        position: absolute;
        color: var(--fg-color);
        font: 12px monospace;
        line-height: 1.5em;
        padding: 0;
        border-radius: 10px;
        border-style: solid;
        border-width: medium;
        border-color: var(--border-color);
        z-index: 1000;
        overflow: hidden;
        max-width: 500px;
        max-height: 450px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
      }
      .rt-content-wrapper {
        overflow-y: auto;
        overflow-x: hidden;
        max-height: calc(450px - 30px);
        padding: 10px;
        box-sizing: border-box;
      }
      .rt-content-wrapper::-webkit-scrollbar {
        width: 6px;
        height: 6px;
      }
      .rt-content-wrapper::-webkit-scrollbar-track {
        background: var(--comfy-bg);
        border-radius: 3px;
      }
      .rt-content-wrapper::-webkit-scrollbar-thumb {
        background-color: var(--fg-color);
        border-radius: 3px;
        border: 2px solid var(--comfy-bg);
      }
      .rt-content-wrapper::-webkit-scrollbar-corner {
        background: var(--comfy-bg);
      }
      .rt-content-wrapper {
        scrollbar-width: thin;
        scrollbar-color: var(--fg-color) var(--comfy-bg);
      }
      .rt-content-wrapper a { 
        color: #4ade80; 
        text-decoration: underline;
      }
      .rt-content-wrapper a:visited { 
        color: #86efac; 
      }
      .rt-content-wrapper a:hover { 
        color: #22c55e; 
      }
      .rt-content-wrapper pre { 
        margin: 5px 0; 
        padding: 8px; 
        background: var(--comfy-bg); 
        border-radius: 4px;
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-all;
      }
      .rt-content-wrapper code { 
        background: var(--comfy-bg); 
        padding: 2px 4px; 
        border-radius: 3px;
        font-size: 11px;
      }
      .rt-content-wrapper h1 {
        font-size: 16px;
        font-weight: bold;
        margin: 0 0 8px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid var(--border-color);
        color: #4ade80;
      }
      .rt-content-wrapper h2 {
        font-size: 14px;
        font-weight: bold;
        margin: 8px 0 4px 0;
        color: #86efac;
      }
      .rt-content-wrapper h3 {
        font-size: 13px;
        font-weight: bold;
        margin: 6px 0 3px 0;
        color: #bbf7d0;
      }
      .rt-content-wrapper ul, .rt-content-wrapper ol {
        margin: 4px 0;
        padding-left: 20px;
      }
      .rt-content-wrapper li {
        margin: 2px 0;
      }
      .rt-content-wrapper table {
        width: 100%;
        border-collapse: collapse;
        margin: 6px 0;
        font-size: 11px;
      }
      .rt-content-wrapper th, .rt-content-wrapper td {
        border: 1px solid var(--border-color);
        padding: 4px 6px;
        text-align: left;
      }
      .rt-content-wrapper th {
        background: var(--comfy-bg);
        font-weight: bold;
      }
      .rt-content-wrapper blockquote {
        border-left: 3px solid #4ade80;
        margin: 6px 0;
        padding-left: 10px;
        color: #a1a1aa;
        font-style: italic;
      }
    `;
    document.head.appendChild(styleTag);
  }
};

// 创建弹窗 - 修复滚动条问题
function createDocPopup(description, signal, onClose, opts = {}) {
  create_documentation_stylesheet();
  
  const docElement = document.createElement('div');
  const contentWrapper = document.createElement('div');
  docElement.appendChild(contentWrapper);
  
  contentWrapper.classList.add('rt-content-wrapper');
  docElement.classList.add('rt-documentation-popup');
  
  // 渲染 Markdown
  if (app.extensionManager?.renderMarkdownToHtml) {
    contentWrapper.innerHTML = app.extensionManager.renderMarkdownToHtml(description);
  } else if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
    contentWrapper.innerHTML = DOMPurify.sanitize(marked.parse(description));
  } else {
    const escaped = description
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/(^|[^"'])(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank">$2</a>')
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^\s*### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^\s*## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^\s*# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\n/g, '<br>');
    contentWrapper.innerHTML = escaped;
  }
  
  // 关闭按钮
  const closeButton = document.createElement('div');
  closeButton.textContent = '✕';
  closeButton.style.cssText = `
    position: absolute; 
    top: 4px; 
    right: 4px; 
    cursor: pointer;
    padding: 2px 6px; 
    color: var(--fg-color); 
    font-size: 14px;
    background: var(--comfy-bg);
    border-radius: 4px;
    border: 1px solid var(--border-color);
    line-height: 1;
    transition: background 0.2s;
  `;
  closeButton.addEventListener('mouseenter', () => {
    closeButton.style.background = '#ef4444';
    closeButton.style.color = '#fff';
  });
  closeButton.addEventListener('mouseleave', () => {
    closeButton.style.background = 'var(--comfy-bg)';
    closeButton.style.color = 'var(--fg-color)';
  });
  closeButton.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    onClose();
  }, { signal });
  docElement.appendChild(closeButton);
  
  document.body.appendChild(docElement);
  return { docElement, contentWrapper };
}

// Legacy Canvas 模式：添加文档按钮
const addDocumentation = (nodeData, nodeType, opts = {}) => {
  opts = opts || {};
  const iconSize = opts.icon_size || 14;
  const iconMargin = opts.icon_margin || 4;
  let docElement = null;
  let contentWrapper = null;
  
  if (!nodeData.description) return;
  
  const drawFg = nodeType.prototype.onDrawForeground;
  nodeType.prototype.onDrawForeground = function(ctx) {
    const r = drawFg ? drawFg.apply(this, arguments) : undefined;
    if (this.flags.collapsed) return r;
    
    const x = this.size[0] - iconSize - iconMargin;
    
    // 创建弹窗
    if (this.show_rt_doc && docElement === null) {
      const popup = createDocPopup(
        nodeData.description,
        this.rtDocCtrl.signal,
        () => {
          this.show_rt_doc = false;
          docElement.parentNode.removeChild(docElement);
          docElement = null;
          contentWrapper = null;
        },
        { scaleResize: true }
      );
      docElement = popup.docElement;
      contentWrapper = popup.contentWrapper;
    }
    
    // 关闭弹窗
    else if (!this.show_rt_doc && docElement !== null) {
      docElement.parentNode.removeChild(docElement);
      docElement = null;
    }
    
    // 更新弹窗位置
    if (this.show_rt_doc && docElement !== null) {
      const rect = ctx.canvas.getBoundingClientRect();
      const scaleX = rect.width / ctx.canvas.width;
      const scaleY = rect.height / ctx.canvas.height;
      const transform = new DOMMatrix()
        .scaleSelf(scaleX, scaleY)
        .multiplySelf(ctx.getTransform())
        .translateSelf(this.size[0] * scaleX * Math.max(1.0, window.devicePixelRatio), 0)
        .translateSelf(10, -32);
      const scale = new DOMMatrix().scaleSelf(transform.a, transform.d);
      const bcr = app.canvas.canvas.getBoundingClientRect();
      
      Object.assign(docElement.style, {
        transformOrigin: '0 0',
        transform: scale,
        left: `${transform.a + bcr.x + transform.e}px`,
        top: `${transform.d + bcr.y + transform.f}px`,
      });
    }
    
    // 绘制问号图标
    ctx.save();
    ctx.translate(x - 2, iconSize - 34);
    ctx.scale(iconSize / 32, iconSize / 32);
    ctx.font = 'bold 36px monospace';
    ctx.fillStyle = '#4ade80'; // 绿色
    ctx.fillText('?', 0, 24);
    ctx.restore();
    
    return r;
  };
  
  // 点击处理
  const mouseDown = nodeType.prototype.onMouseDown;
  nodeType.prototype.onMouseDown = function(e, localPos, canvas) {
    const r = mouseDown ? mouseDown.apply(this, arguments) : undefined;
    const iconX = this.size[0] - iconSize - iconMargin;
    const iconY = iconSize - 34;
    
    if (localPos[0] > iconX && localPos[0] < iconX + iconSize &&
        localPos[1] > iconY && localPos[1] < iconY + iconSize) {
      this.show_rt_doc = !this.show_rt_doc;
      if (this.show_rt_doc) {
        this.rtDocCtrl = new AbortController();
      } else {
        this.rtDocCtrl.abort();
      }
      return true;
    }
    return r;
  };
  
  // 节点删除时清理
  const onRem = nodeType.prototype.onRemoved;
  nodeType.prototype.onRemoved = function() {
    const r = onRem ? onRem.apply(this, []) : undefined;
    if (docElement) {
      docElement.remove();
      docElement = null;
      contentWrapper = null;
    }
    return r;
  };
};

// Vue 节点模式
const popupState = new Map();

function getNodeById(nodeId) {
  return app.graph?.getNodeById(nodeId);
}

function closeNodePopup(nodeId) {
  const state = popupState.get(nodeId);
  if (!state) return;
  if (state.docElement) state.docElement.remove();
  if (state.abortCtrl) state.abortCtrl.abort();
  if (state.animFrame) cancelAnimationFrame(state.animFrame);
  popupState.delete(nodeId);
}

function openNodePopup(nodeId, description) {
  closeNodePopup(nodeId);
  const state = popupState.get(nodeId) || {};
  popupState.set(nodeId, state);
  
  state.abortCtrl = new AbortController();
  const popup = createDocPopup(
    description,
    state.abortCtrl.signal,
    () => closeNodePopup(nodeId),
    { scaleResize: false }
  );
  state.docElement = popup.docElement;
  
  function updatePosition() {
    if (!state.docElement || !state.docElement.parentNode) return;
    const nodeEl = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (nodeEl) {
      const rect = nodeEl.getBoundingClientRect();
      state.docElement.style.left = `${rect.right + 10}px`;
      state.docElement.style.top = `${rect.top}px`;
    }
    state.animFrame = requestAnimationFrame(updatePosition);
  }
  state.animFrame = requestAnimationFrame(updatePosition);
}

function tryInjectHelpButton(header) {
  if (header.querySelector('.rt-help-btn')) return;
  
  const nodeEl = header.closest('[data-node-id]');
  if (!nodeEl) return;
  const nodeId = nodeEl.dataset.nodeId;
  const node = getNodeById(nodeId);
  if (!node) return;
  
  const description = node._rtHelpDescription;
  if (!description) return;
  
  const flexContainer = header.querySelector(':scope > div');
  if (!flexContainer) return;
  
  const helpBtn = document.createElement('span');
  helpBtn.className = 'rt-help-btn';
  helpBtn.textContent = '?';
  helpBtn.style.cssText = `
    color: #4ade80; font-weight: bold; font-size: 14px;
    cursor: pointer; flex-shrink: 0; padding: 0 4px;
    line-height: 1; user-select: none;
  `;
  helpBtn.title = 'Show help';
  helpBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const state = popupState.get(nodeId);
    if (state?.docElement) {
      closeNodePopup(nodeId);
    } else {
      openNodePopup(nodeId, description);
    }
  });
  flexContainer.appendChild(helpBtn);
}

function setupHelpObserver() {
  document.querySelectorAll('.lg-node-header').forEach(tryInjectHelpButton);
  
  let pending = false;
  const observer = new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      document.querySelectorAll('.lg-node-header:not(:has(.rt-help-btn))').forEach(tryInjectHelpButton);
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
}