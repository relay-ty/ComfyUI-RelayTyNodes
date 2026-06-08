/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - 国际化 (i18n) 前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   在节点创建后，将 INPUT_TYPES 中的英文参数名替换为中文显示名，
 *   同时翻译输出端口名称。
 *
 * 翻译数据来源:
 *   locales/zh/nodeDefs.json（22 个节点的完整翻译）
 *
 * 适用环境:
 *   - 新版 ComfyUI：通过内置 i18n 系统自动加载 nodeDefs.json
 *   - 旧版 ComfyUI：通过本 JS 扩展手动应用翻译（兜底）
 *
 * =============================================================================
 */

const { app } = window.comfyAPI.app;

const TRANSLATIONS = {
    "RT_LazySwitch": {
        display_name: "RT惰性开关",
        inputs: {
            condition: "条件",
            on_true: "条件为真",
            on_false: "条件为假"
        },
        outputs: {
            output: "输出"
        }
    },
    "RT_LazySwitch2way": {
        display_name: "RT双路惰性开关",
        inputs: {
            condition: "条件",
            on_true_1: "条件为真①",
            on_true_2: "条件为真②",
            on_false_1: "条件为假①",
            on_false_2: "条件为假②"
        },
        outputs: {
            output1: "输出①",
            output2: "输出②"
        }
    },
    "RT_ResolutionSelector": {
        display_name: "RT分辨率选择器",
        inputs: { resolution: "分辨率" },
        outputs: { resolution: "分辨率" }
    },
    "RT_AspectRatioSelector": {
        display_name: "RT比例选择器",
        inputs: { aspect_ratio: "宽高比" },
        outputs: { aspect_ratio: "宽高比" }
    },
    "RT_AspectRatioDetector": {
        display_name: "RT比例检测器",
        inputs: { image: "图像" },
        outputs: { aspect_ratio: "宽高比" }
    },
    "RT_MaskExpand": {
        display_name: "RT遮罩扩展/收缩",
        inputs: {
            mask: "遮罩",
            expand: "扩展量",
            tapered_corners: "渐变角落",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { mask: "遮罩" }
    },
    "RT_MaskFeather": {
        display_name: "RT遮罩高斯羽化",
        inputs: {
            mask: "遮罩",
            kernel: "羽化范围",
            sigma: "羽化强度",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { mask: "遮罩" }
    },
    "RT_SeparateMasks": {
        display_name: "RT遮罩分离",
        inputs: {
            masks: "遮罩序列",
            area_threshold: "面积阈值",
            max_tracks: "最大跟踪数"
        },
        outputs: {
            all_tracks: "全部轨迹",
            num_tracks: "轨迹数量"
        }
    },
    "RT_GetTrack": {
        display_name: "RT获取Track",
        inputs: {
            all_tracks: "全部轨迹",
            track_index: "轨迹索引"
        },
        outputs: { track: "轨迹" }
    },
    "RT_BatchMask": {
        display_name: "RT复制遮罩批次",
        inputs: {
            mask: "遮罩",
            count: "复制数量"
        },
        outputs: { masks: "遮罩" }
    },
    "RT_GetMaskFromBatch": {
        display_name: "RT从批次获取遮罩",
        inputs: {
            masks: "遮罩批次",
            batch_index: "批次索引",
            length: "获取数量"
        },
        outputs: { mask: "遮罩" }
    },
    "RT_ImageToMask": {
        display_name: "RT图像通道转遮罩",
        inputs: {
            image: "图像",
            channel: "通道",
            black_point: "黑点",
            white_point: "白点",
            gamma: "伽马",
            invert: "反转遮罩",
            mask: "遮罩",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { mask: "遮罩" }
    },
    "RT_MaskToImage": {
        display_name: "RT遮罩转图像",
        inputs: {
            mask: "遮罩",
            color: "颜色",
            invert: "反转遮罩",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { image: "图像" }
    },
    "RT_BBoxToMask": {
        display_name: "RTBBox转遮罩",
        inputs: {
            image: "图像",
            bboxes: "边界框",
            dilation: "扩展像素",
            feather: "羽化半径",
            chunk_size: "分块大小",
            device: "设备"
        },
        outputs: { mask: "遮罩" }
    },
    "RT_MaskContour": {
        display_name: "RT遮罩描边",
        inputs: {
            images: "图像",
            mask: "遮罩",
            line_width: "线宽"
        },
        outputs: { images: "图像" }
    },
    "RT_DrawMaskOnImage": {
        display_name: "RT遮罩绘制",
        inputs: {
            image: "图像",
            mask: "遮罩",
            color: "颜色",
            opacity: "不透明度",
            device: "设备",
            batch_size: "批次大小"
        },
        outputs: { image: "图像" }
    },
    "RT_JoinStringMulti": {
        display_name: "RT多字符串连接",
        inputs: {
            inputcount: "输入数量",
            delimiter: "分隔符",
            clean_whitespace: "清理空白",
            return_list: "返回列表",
            string_1: "字符串①",
            string_2: "字符串②"
        },
        outputs: { string: "字符串" }
    },
    "RT_JoinStrings": {
        display_name: "RT双字符串连接",
        inputs: {
            delimiter: "分隔符",
            clean_whitespace: "清理空白",
            string1: "字符串①",
            string2: "字符串②"
        },
        outputs: { string: "字符串" }
    },
    "RT_MathExpression": {
        display_name: "RT数学表达式",
        inputs: {
            expression: "表达式",
            inputcount: "输入数量",
            a: "a",
            b: "b"
        },
        outputs: {
            float: "浮点",
            int: "整数",
            bool: "布尔"
        }
    },
    "RT_ColorMatch": {
        display_name: "RT颜色匹配",
        inputs: {
            image_ref: "参考图像",
            image_target: "目标图像",
            method: "算法",
            strength: "强度",
            device: "设备",
            batch_size: "批次大小"
        },
        outputs: { image: "图像" }
    },
    "RT_PoissonBlend": {
        display_name: "RT泊松融合",
        inputs: {
            original: "原图",
            inpaint: "修复图",
            mask: "遮罩",
            poisson_iters: "迭代次数",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { image: "图像" }
    },
    "RT_PoissonBlendV2": {
        display_name: "RT泊松融合V2",
        inputs: {
            original: "原图",
            inpaint: "修复图",
            mask: "遮罩",
            poisson_iters: "迭代次数",
            transition_width: "过渡带宽度",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { image: "图像" }
    },
    "RT_BlendInpaint": {
        display_name: "RT遮罩混合",
        inputs: {
            original: "原图",
            inpaint: "修复图",
            mask: "遮罩",
            batch_size: "批次大小",
            device: "设备"
        },
        outputs: { image: "图像" }
    }
};

app.registerExtension({
    name: "RelayTyNodes.i18n",

    beforeRegisterNodeDef(nodeType, nodeData) {
        const nodeName = nodeData.name;
        const i18n = TRANSLATIONS[nodeName];
        if (!i18n) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated || function () { };

        nodeType.prototype.onNodeCreated = function () {
            originalOnNodeCreated.apply(this, arguments);

            setTimeout(() => {
                if (i18n.inputs) {
                    for (const widget of this.widgets || []) {
                        const zhName = i18n.inputs[widget.name];
                        if (zhName) {
                            widget.label = zhName;
                        }
                    }
                }

                if (i18n.outputs) {
                    for (const output of this.outputs || []) {
                        const zhName = i18n.outputs[output.name];
                        if (zhName) {
                            output.label = zhName;
                        }
                    }
                }
            }, 0);
        };
    }
});
