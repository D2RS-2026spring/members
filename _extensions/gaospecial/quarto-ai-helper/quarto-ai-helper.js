/* quarto-ai-helper.js */
(function () {
  // ── i18n 多语言支持（根据浏览器/系统语言自动切换）──────────────────────
  var lang = (navigator.language || navigator.userLanguage || "en").toLowerCase();
  var isChinese = lang.startsWith("zh");

  var i18n = {
    zh: {
      askChatGPT: "🤖 问问 ChatGPT",
      copyPrompt: "📋 复制提问到其它大模型",
      copied: "✅ 已复制到剪贴板",
      errorLabel: "⚠️ 代码运行出错",
      chatTooltip: "将源代码和报错信息发送给 ChatGPT，获取修复建议",
      copyTooltip: "复制格式化的提问内容到剪贴板，方便粘贴到其它大模型",
      promptTemplate: function (source, error, language) {
        return "我在 Quarto 文档中运行 " + language + " 代码时遇到了报错，请帮我分析原因并修复代码。\n\n" +
          "## 源代码\n\n" +
          "```" + language.toLowerCase() + "\n" + source + "\n```\n\n" +
          "## 报错信息\n\n" +
          "```\n" + error + "\n```\n\n" +
          "请用 Markdown 格式回答，解释原因并给出修复后的代码。";
      },
      noSource: "（无法获取源代码）"
    },
    en: {
      askChatGPT: "🤖 Ask ChatGPT",
      copyPrompt: "📋 Copy prompt for other AI",
      copied: "✅ Copied to clipboard",
      errorLabel: "⚠️ Code Error",
      chatTooltip: "Send the source code and error message to ChatGPT for a fix",
      copyTooltip: "Copy a formatted prompt to clipboard for use with other AI models",
      promptTemplate: function (source, error, language) {
        return "I encountered an error while running " + language + " code in a Quarto document. " +
          "Please help me diagnose the issue and fix the code.\n\n" +
          "## Source Code\n\n" +
          "```" + language.toLowerCase() + "\n" + source + "\n```\n\n" +
          "## Error Message\n\n" +
          "```\n" + error + "\n```\n\n" +
          "Please respond in Markdown format with a brief explanation and the fixed code.";
      },
      noSource: "(Source code not available)"
    }
  };

  var t = isChinese ? i18n.zh : i18n.en;

  // ── 辅助函数：检测代码语言 ─────────────────────────────────────────────
  function detectLanguage(sourceCodeBlock) {
    if (!sourceCodeBlock) return "R";
    var classList = sourceCodeBlock.className || "";
    if (classList.indexOf("python") !== -1) return "Python";
    if (classList.indexOf("julia") !== -1) return "Julia";
    if (classList.indexOf("bash") !== -1) return "Bash";
    if (classList.indexOf("js") !== -1 || classList.indexOf("javascript") !== -1) return "JavaScript";
    return "R";
  }

  // ── 辅助函数：获取完整的源代码 ────────────────────────────────────────
  function getSourceCode(parentCell) {
    if (!parentCell) return null;
    var codeBlocks = parentCell.querySelectorAll("pre.sourceCode");
    if (codeBlocks.length === 0) return null;
    var parts = [];
    for (var i = 0; i < codeBlocks.length; i++) {
      var code = codeBlocks[i].innerText.trim();
      if (code) parts.push(code);
    }
    return parts.length > 0 ? parts.join("\n\n") : null;
  }

  // ── 主逻辑 ──────────────────────────────────────────────────────────────
  function initAIHelper() {
    var errorBlocks = document.querySelectorAll(".cell-output-error");

    errorBlocks.forEach(function (block) {
      // 避免重复添加
      if (block.classList.contains("ai-helper-styled")) return;

      // 找到所属 cell
      var parentCell = block.closest(".cell");

      // 获取源代码块（用于检测语言）
      var firstSourceBlock = parentCell
        ? parentCell.querySelector("pre.sourceCode")
        : null;

      // 检测编程语言
      var language = detectLanguage(firstSourceBlock);

      // 先保存原始错误文本（在修改 DOM 之前）
      var originalErrorText = block.innerText.trim();

      // ── 给错误块添加样式类 ────────────────────────────────────────────
      block.classList.add("ai-helper-styled");

      // ── 在错误信息顶部添加标签 ────────────────────────────────────────
      var label = document.createElement("div");
      label.className = "ai-helper-error-label";
      label.textContent = t.errorLabel;
      block.insertBefore(label, block.firstChild);

      // 构造发送给大模型的完整 prompt
      var getFullPrompt = function () {
        var sourceCode = getSourceCode(parentCell) || t.noSource;
        return t.promptTemplate(sourceCode, originalErrorText, language);
      };

      // ── 按钮容器（放在错误块内部底部）─────────────────────────────────
      var container = document.createElement("div");
      container.className = "quarto-ai-helper-buttons";

      // ── ChatGPT 按钮 ─────────────────────────────────────────────────────
      var chatBtn = document.createElement("button");
      chatBtn.innerText = t.askChatGPT;
      chatBtn.className = "btn btn-success btn-sm";
      chatBtn.title = t.chatTooltip;
      chatBtn.onclick = function () {
        var prompt = getFullPrompt();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(prompt).catch(function () {});
        }
        window.open(
          "https://chatgpt.com/?q=" + encodeURIComponent(prompt),
          "_blank"
        );
      };

      // ── 复制按钮 ─────────────────────────────────────────────────────────
      var copyBtn = document.createElement("button");
      copyBtn.innerText = t.copyPrompt;
      copyBtn.className = "btn btn-outline-secondary btn-sm";
      copyBtn.title = t.copyTooltip;
      copyBtn.onclick = function () {
        var prompt = getFullPrompt();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(prompt).then(function () {
            var original = copyBtn.innerText;
            copyBtn.innerText = t.copied;
            setTimeout(function () {
              copyBtn.innerText = original;
            }, 2000);
          });
        } else {
          var ta = document.createElement("textarea");
          ta.value = prompt;
          ta.style.position = "fixed";
          ta.style.opacity = "0";
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          try {
            document.execCommand("copy");
            var original = copyBtn.innerText;
            copyBtn.innerText = t.copied;
            setTimeout(function () {
              copyBtn.innerText = original;
            }, 2000);
          } catch (e) {}
          document.body.removeChild(ta);
        }
      };

      container.appendChild(chatBtn);
      container.appendChild(copyBtn);

      // 按钮放在错误块内部底部
      block.appendChild(container);
    });
  }

  // ── 确保 DOM 已就绪后执行 ────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAIHelper);
  } else {
    initAIHelper();
  }
})();
