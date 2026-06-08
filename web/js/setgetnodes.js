/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - RT_GetNode 扩展模块
 * =============================================================================
 * 
 * 模块说明:
 *   本模块作为 KJNodes Set/Get 节点的补充，仅提供 RT_GetNode 节点。
 *   用于获取 KJNodes 的 SetNode 值，实现跨节点数据传递。
 * 
 * 扩展功能:
 *   - 提供 match 过滤输入框，可按名称快速筛选 SetNode
 *   - 支持跨子图查找 SetNode
 *   - 右键菜单提供"Go to setter"功能
 * 
 * 依赖关系:
 *   - 依赖 KJNodes 扩展提供的 SetNode 节点
 *   - 使用 ComfyUI 的 LiteGraph 框架
 * 
 * 使用方式:
 *   1. 安装 KJNodes 扩展
 *   2. 在 KJNodes 中创建 SetNode
 *   3. 在 RelayTyNodes 中创建 RT_GetNode
 *   4. 使用 match 框过滤，在下拉框中选择要获取的 SetNode 名称
 * 
 * =============================================================================
 */

// 获取 ComfyUI 应用实例
const { app } = window.comfyAPI.app;

// =============================================================================
// 节点颜色配置
// =============================================================================

let _typeColorMap;

/**
 * 设置节点的颜色和背景色
 * @param {LGraphNode} node - 要设置颜色的节点
 * @param {string} type - 节点类型
 */
function setColorAndBgColor(node, type) {
    if (!_typeColorMap) {
        _typeColorMap = {
            "DEFAULT": LGraphCanvas.node_colors.gray,
            "MODEL": LGraphCanvas.node_colors.blue,
            "LATENT": LGraphCanvas.node_colors.purple,
            "VAE": LGraphCanvas.node_colors.red,
            "WANVAE": LGraphCanvas.node_colors.red,
            "CONDITIONING": LGraphCanvas.node_colors.brown,
            "IMAGE": LGraphCanvas.node_colors.pale_blue,
            "CLIP": LGraphCanvas.node_colors.yellow,
            "FLOAT": LGraphCanvas.node_colors.green,
            "MASK": { color: "#1c5715", bgcolor: "#1f401b" },
            "INT": { color: "#1b4669", bgcolor: "#29699c" },
            "CONTROL_NET": { color: "#156653", bgcolor: "#1c453b" },
            "NOISE": { color: "#2e2e2e", bgcolor: "#242121" },
            "GUIDER": { color: "#3c7878", bgcolor: "#1c453b" },
            "SAMPLER": { color: "#614a4a", bgcolor: "#3b2c2c" },
            "SIGMAS": { color: "#485248", bgcolor: "#272e27" },
        };
    }
    const colors = _typeColorMap[type] || LGraphCanvas.node_colors?.gray;
    if (colors) {
        node.color = colors.color;
        node.bgcolor = colors.bgcolor;
    }
}

/**
 * 根据设置自动设置节点颜色
 * @param {LGraphNode} node - 要设置颜色的节点
 * @param {string} type - 节点类型
 */
function autoColor(node, type) {
    if (!app.ui.settings.getSettingValue("RelayTyNodes.nodeAutoColor") ?? false) return;
    if (type === '*') { node.color = null; node.bgcolor = null; }
    else setColorAndBgColor(node, type);
}

// =============================================================================
// 图结构工具函数
// =============================================================================

const LGraphNode = LiteGraph.LGraphNode;

/**
 * 获取图的根图
 * @param {LGraph} graph - 输入的图
 * @returns {LGraph|null} 根图
 */
function findRootGraph(graph) {
    if (!graph) return null;
    return graph.rootGraph || graph;
}

/**
 * 获取从当前图到根图的祖先图链
 * @param {LGraph} graph - 起始图
 * @returns {LGraph[]} 图的祖先链数组
 */
function getGraphAncestors(graph) {
    if (!graph) return [];
    const root = findRootGraph(graph);
    if (!root || graph === root) return [root];

    const chain = [graph];
    const visited = new Set([graph]);
    let current = graph;

    while (current !== root && !visited.has(root)) {
        let found = false;
        
        // 检查根图的节点
        for (const n of root._nodes) {
            if (n.subgraph === current) {
                chain.push(root);
                current = root;
                found = true;
                break;
            }
        }
        if (found) break;
        
        // 检查子图（避免递归）
        const subgraphs = root._subgraphs || root.subgraphs;
        if (subgraphs) {
            for (const sg of subgraphs.values()) {
                if (sg !== current && !visited.has(sg) && sg._nodes) {
                    for (const n of sg._nodes) {
                        if (n.subgraph === current) {
                            visited.add(sg);
                            chain.push(sg);
                            current = sg;
                            found = true;
                            break;
                        }
                    }
                    if (found) break;
                }
            }
        }
        if (!found) break;
    }
    
    return chain;
}

/**
 * 在多个图中收集指定类型的节点
 * @param {LGraph[]} graphs - 要搜索的图数组
 * @param {string} type - 节点类型
 * @returns {Array<{node: LGraphNode, graph: LGraph}>} 匹配的节点及其所在图
 */
function collectNodesOfType(graphs, type) {
    const result = [];
    for (const g of graphs) {
        if (!g?._nodes) continue;
        for (const n of g._nodes) {
            if (n.type === type) {
                result.push({ node: n, graph: g });
            }
        }
    }
    return result;
}

// =============================================================================
// SetNode 查找函数
// =============================================================================

const SET_NODE_TYPES = ['SetNode'];

/**
 * 根据名称查找 SetNode
 * @param {LGraph} graph - 起始图
 * @param {string} name - SetNode 的名称
 * @returns {Object|null} 包含 node 和 graph 的对象
 */
function findSetterByName(graph, name) {
    if (!name) return null;
    for (const g of getGraphAncestors(graph)) {
        if (!g?._nodes) continue;
        for (const node of g._nodes) {
            if (SET_NODE_TYPES.includes(node.type) && node.widgets?.[0]?.value === name) {
                return { node, graph: g };
            }
        }
    }
    return null;
}

// =============================================================================
// 辅助函数
// =============================================================================

/**
 * 获取指定 ID 的链接对象（兼容多种 LiteGraph 版本）
 * @param {LGraph} graph - 图
 * @param {number} linkId - 链接 ID
 * @returns {Object|null} 链接对象
 */
function getLink(graph, linkId) {
    if (linkId == null) return null;
    if (graph.getLink) return graph.getLink(linkId);
    if (!graph._links) return null;
    
    if (graph._links instanceof Map) {
        return graph._links.get(linkId);
    } else if (Array.isArray(graph._links)) {
        return graph._links.find(l => l.id === linkId);
    } else {
        return graph._links?.[linkId] ?? null;
    }
}

/**
 * 显示警告信息
 * @param {string} msg - 警告消息
 * @param {LGraphNode} node - 相关的节点
 */
function showAlert(msg, node) {
    console.error(`[RelayTyNodes] ${msg}`);
    if (node && app.canvas) {
        try {
            app.canvas.centerOnNode(node);
            app.canvas.selectNode(node, false);
        } catch (e) {
            console.error('[RelayTyNodes] Error in showAlert:', e);
        }
    }
}

// =============================================================================
// SetNode 名称管理
// =============================================================================

const _setNameSourceMap = new Map();

/**
 * 获取可见的 SetNode 名称列表
 * @param {LGraph} graph - 当前图
 * @param {string|null} filterType - 类型过滤器
 * @param {string} matchFilter - 名称过滤字符串
 * @returns {string[]} 排序后的 SetNode 名称数组
 */
function getVisibleSetNames(graph, filterType = null, matchFilter = '*') {
    const names = new Set();
    const ancestors = getGraphAncestors(graph);
    
    for (const type of SET_NODE_TYPES) {
        const entries = collectNodesOfType(ancestors, type);
        for (const { node, graph: nodeGraph } of entries) {
            const name = node.widgets?.[0]?.value;
            if (!name || name === '' || name === '*') continue;
            
            // 类型过滤：支持多类型匹配
            if (filterType && filterType !== '*') {
                const nodeType = node.inputs?.[0]?.type;
                if (nodeType && nodeType !== '*') {
                    const filterTypes = String(filterType).split(",");
                    const nodeTypes = String(nodeType).split(",");
                    const hasMatch = filterTypes.some(ft => 
                        ft === nodeType || nodeTypes.includes(ft)
                    );
                    if (!hasMatch) continue;
                }
            }
            
            // 名称过滤：模糊匹配
            if (matchFilter !== '*') {
                const filterLower = matchFilter.toLowerCase();
                if (!name.toLowerCase().includes(filterLower)) continue;
            }
            
            names.add(name);
            _setNameSourceMap.set(name, nodeGraph === graph ? "local" : "parent");
        }
    }
    
    return Array.from(names).sort();
}

// =============================================================================
// RT_GetNode 节点类定义
// =============================================================================

app.registerExtension({
    name: "RelayTyNodes.GetNode",
    
    registerCustomNodes() {
        // 检查 KJNodes 是否可用
        const hasKJNodes = typeof LiteGraph !== 'undefined' && LiteGraph.getNodeType && 
                          LiteGraph.getNodeType("SetNode") !== undefined;
        
        if (!hasKJNodes) {
            console.warn("[RelayTyNodes] KJNodes extension not found. RT_GetNode requires KJNodes SetNode to function properly.");
        }
        
        class GetNode extends LGraphNode {
            static title = "RT_GetNode";
            static category = "RelayTyNodes";
            serialize_widgets = true;
            drawConnection = false;
            currentSetter = null;
            canvas = app.canvas;

            constructor(title) {
                super(title);
                
                if (!this.properties) {
                    this.properties = {};
                }
                this.properties["Node name for S&R"] = "RT_GetNode";
                this.properties["aux_id"] = "relay-ty/ComfyUI-RelayTyNodes";
                this.isVirtualNode = true;

                const comboOptions = {
                    getOptionLabel: (value) => {
                        if (!value) return "";
                        const source = _setNameSourceMap.get(value);
                        if (!source || source === "local") return value;
                        return `${value} (${source})`;
                    },
                };

                Object.defineProperty(comboOptions, 'values', {
                    get: () => {
                        if (!this.graph) return [];
                        
                        let filterType = null;
                        if (app.ui.settings.getSettingValue("RelayTyNodes.filterGetNodeOptions") !== false
                            && this.outputs[0]?.links?.length) {
                            const linkId = this.outputs[0].links[0];
                            const link = getLink(this.graph, linkId);
                            if (link) {
                                const targetNode = this.graph.getNodeById(link.target_id);
                                filterType = targetNode?.inputs?.[link.target_slot]?.type || null;
                            }
                        }
                        
                        const matchFilter = this.widgets?.[0]?.value || '*';
                        return getVisibleSetNames(this.graph, filterType, matchFilter);
                    },
                    enumerable: true,
                    configurable: true
                });

                // 添加 match 过滤输入框（扩展功能）
                this.addWidget("text", "match", "", () => {
                    if (!this.graph || app.configuringGraph) return;
                    this.onRename();
                });

                // 添加 Constant 下拉选择框
                this.addWidget("combo", "Constant", "", () => { 
                    if (!app.configuringGraph) this.onRename(); 
                }, comboOptions);

                // 添加输出端口
                this.addOutput("*", '*');
            }

            onConnectionsChange() {
                if (app.configuringGraph) return;
                this.validateLinks();
            }

            setName(name) {
                if (this.widgets?.[1]) {
                    this.widgets[1].value = name;
                    this.onRename();
                    this.serialize();
                }
            }

            onRename() {
                const setter = this.findSetter(this.graph);
                if (setter) {
                    this.setType(setter.inputs[0].type);
                } else {
                    this.setType('*');
                }
                app.canvas?.setDirty(true, true);
            }

            clone() {
                const cloned = super.clone();
                cloned.size = cloned.computeSize();
                return cloned;
            }

            validateLinks() {
                if (this.outputs[0].type !== '*' && this.outputs[0].links && this.graph) {
                    this.outputs[0].links.filter(linkId => {
                        const link = getLink(this.graph, linkId);
                        if (!link || !link.type) return false;
                        if (link.type === '*') return false;
                        const targetNode = this.graph.getNodeById(link.target_id);
                        const targetType = targetNode?.inputs?.[link.target_slot]?.type;
                        if (targetType === '*') return false;
                        if (targetType) {
                            const targetTypes = String(targetType).split(",");
                            if (targetTypes.includes(this.outputs[0].type)) return false;
                        }
                        return !link.type.split(",").includes(this.outputs[0].type);
                    }).forEach(linkId => {
                        this.graph.removeLink(linkId);
                    });
                }
            }

            setType(type) {
                this.outputs[0].name = type;
                this.outputs[0].type = type;
                this.validateLinks();
                autoColor(this, type);
            }

            findSetter(graph) {
                const name = this.widgets?.[1]?.value;
                const result = findSetterByName(graph, name);
                return result ? result.node : undefined;
            }

            goToSetter() {
                if (!this.currentSetter) return;
                const setterGraph = this.currentSetter.graph;
                if (setterGraph && setterGraph !== this.graph) {
                    this.canvas.setGraph(setterGraph);
                    setTimeout(() => {
                        try {
                            this.canvas.centerOnNode(this.currentSetter);
                            this.canvas.selectNode(this.currentSetter, false);
                            this.canvas.setDirty(true, true);
                        } catch (e) {
                            console.error('[RelayTyNodes] Error in goToSetter:', e);
                        }
                    }, 0);
                } else {
                    try {
                        this.canvas.centerOnNode(this.currentSetter);
                        this.canvas.selectNode(this.currentSetter, false);
                    } catch (e) {
                        console.error('[RelayTyNodes] Error in goToSetter:', e);
                    }
                }
            }

            onAdded() {
                this._justAdded = true;
            }

            onConfigure() {
                if (this._justAdded && !app.configuringGraph) {
                    setTimeout(() => this.onRename(), 0);
                }
                this._justAdded = false;
            }

            getInputLink(slot) {
                const name = this.widgets?.[1]?.value;
                if (!name || name === '') return null;

                // 先在当前图中查找
                const setter = this.graph?._nodes?.find(
                    n => SET_NODE_TYPES.includes(n.type) && n.widgets?.[0]?.value === name
                );

                if (setter) {
                    const slotInfo = setter.inputs[slot];
                    if (!slotInfo || slotInfo.link == null) return null;
                    return getLink(this.graph, slotInfo.link);
                }

                // 跨图查找
                const result = findSetterByName(this.graph, name);
                if (result) {
                    const { node: setterInParent, graph: parentGraph } = result;
                    const slotInfo = setterInParent.inputs[slot];
                    if (!slotInfo || slotInfo.link == null) return null;
                    return getLink(parentGraph, slotInfo.link);
                }

                showAlert("No SetNode found for " + name, this);
                return null;
            }

            resolveVirtualOutput(slot) {
                const name = this.widgets?.[1]?.value;
                const result = findSetterByName(this.graph, name);
                if (!result) return undefined;

                // 同图情况：由 getInputLink 处理
                if (result.graph === this.graph) return undefined;

                // 检查是否有多个同名 SetNode（冲突检测）
                const scopeGraphs = getGraphAncestors(this.graph);
                const scopedSetters = collectNodesOfType(scopeGraphs, 'SetNode')
                    .filter(e => e.node.widgets?.[0]?.value === name);
                if (scopedSetters.length > 1) {
                    showAlert(`Multiple SetNodes named "${name}" found in scope`, this);
                    return undefined;
                }

                const { node: setter, graph: setterGraph } = result;
                const slotInfo = setter.inputs[slot];
                if (!slotInfo || slotInfo.link == null) return undefined;

                const link = getLink(setterGraph, slotInfo.link);
                if (!link) return undefined;

                const sourceNode = setterGraph.getNodeById(link.origin_id);
                if (!sourceNode) return undefined;

                return { node: sourceNode, slot: link.origin_slot };
            }

            getExtraMenuOptions(_, options) {
                this.currentSetter = this.findSetter(this.graph);
                if (!this.currentSetter) return;
                
                const sameGraph = this.currentSetter.graph === this.graph;
                if (sameGraph) {
                    options.unshift(
                        {
                            content: "Go to setter",
                            callback: () => {
                                this.goToSetter();
                            },
                        },
                    );
                } else {
                    const setterGraph = this.currentSetter.graph;
                    const isRoot = setterGraph === findRootGraph(this.graph);
                    options.unshift(
                        {
                            content: `Go to setter (in ${isRoot ? 'parent graph' : 'subgraph'})`,
                            callback: () => {
                                try {
                                    this.canvas.setGraph(setterGraph);
                                    setTimeout(() => {
                                        this.canvas.centerOnNode(this.currentSetter);
                                        this.canvas.selectNode(this.currentSetter, false);
                                        this.canvas.setDirty(true, true);
                                    }, 0);
                                } catch (e) {
                                    console.error('[RelayTyNodes] Error in menu callback:', e);
                                }
                            },
                        },
                    );
                }
            }
        }

        LiteGraph.registerNodeType("RT_GetNode", GetNode);
    },
});
